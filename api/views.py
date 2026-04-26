from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Customer, Loan
from .serializers import CustomerSerializer, LoanSerializer
import math
from .tasks import ingest_customer_data, ingest_loan_data
from datetime import datetime, date
from dateutil.relativedelta import relativedelta


class RegisterView(APIView):
    def post(self, request):
        first_name = request.data.get('first_name')
        last_name = request.data.get('last_name')
        age = request.data.get('age')
        monthly_income = request.data.get('monthly_income')
        phone_number = request.data.get('phone_number')

        if not all([first_name, last_name, age, monthly_income, phone_number]):
            return Response({"error": "All fields are required"}, status=status.HTTP_400_BAD_REQUEST)

        approved_limit = math.floor(36 * monthly_income / 100000) * 100000

        customer = Customer.objects.create(
            first_name=first_name,
            last_name=last_name,
            age=age,
            monthly_salary=monthly_income,
            phone_number=phone_number,
            approved_limit=approved_limit
        )

        response_data = {
            "customer_id": customer.customer_id,
            "name": f"{customer.first_name} {customer.last_name}",
            "age": customer.age,
            "monthly_income": customer.monthly_salary,
            "approved_limit": customer.approved_limit,
            "phone_number": customer.phone_number
        }

        return Response(response_data, status=status.HTTP_201_CREATED)

class IngestDataView(APIView):
    def get(self, request):
        ingest_customer_data.delay()
        ingest_loan_data.delay()
        return Response({"message": "Data ingestion started in the background"}, status=status.HTTP_200_OK)

class CheckEligibilityView(APIView):
    def post(self, request):
        customer_id = request.data.get('customer_id')
        loan_amount = request.data.get('loan_amount')
        interest_rate = request.data.get('interest_rate')
        tenure = request.data.get('tenure')

        if not all([customer_id, loan_amount, interest_rate, tenure]):
            return Response({"error": "All fields are required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            customer = Customer.objects.get(customer_id=customer_id)
        except Customer.DoesNotExist:
            return Response({"error": "Customer not found"}, status=status.HTTP_404_NOT_FOUND)

        # Credit Score Calculation
        credit_score = 0

        # i. Past Loans paid on time
        loans = Loan.objects.filter(customer=customer)
        total_emis_paid_on_time = sum([loan.emis_paid_on_time for loan in loans])
        total_tenure = sum([loan.tenure for loan in loans])
        if total_tenure > 0:
            credit_score += (total_emis_paid_on_time / total_tenure) * 20

        # ii. No of loans taken in past
        credit_score += min(len(loans) * 5, 20)

        # iii. Loan activity in current year
        current_year = datetime.now().year
        loans_in_current_year = loans.filter(start_date__year=current_year)
        credit_score += min(len(loans_in_current_year) * 5, 20)

        # iv. Loan approved volume
        total_loan_amount = sum([loan.loan_amount for loan in loans])
        credit_score += min(total_loan_amount / 10000, 20)
        
        # v. If sum of current loans of customer > approved limit of customer , credit score = 0
        current_loans = loans.filter(end_date__gte=datetime.now().date())
        current_loan_amount = sum([loan.loan_amount for loan in current_loans])
        if current_loan_amount > customer.approved_limit:
            credit_score = 0

        # Final Credit Score
        credit_score = min(credit_score, 100)

        # Loan Approval
        approval = False
        corrected_interest_rate = interest_rate

        if sum([loan.monthly_repayment for loan in current_loans]) > customer.monthly_salary / 2:
            approval = False
        elif credit_score > 50:
            approval = True
        elif 30 < credit_score <= 50:
            if interest_rate > 12:
                approval = True
            else:
                corrected_interest_rate = 12
        elif 10 < credit_score <= 30:
            if interest_rate > 16:
                approval = True
            else:
                corrected_interest_rate = 16
        else:
            approval = False

        # Monthly Installment Calculation (Compound Interest)
        monthly_interest_rate = (corrected_interest_rate / 100) / 12
        monthly_installment = (loan_amount * monthly_interest_rate * (1 + monthly_interest_rate)**tenure) / ((1 + monthly_interest_rate)**tenure - 1)


        response_data = {
            "customer_id": customer_id,
            "approval": approval,
            "interest_rate": interest_rate,
            "corrected_interest_rate": corrected_interest_rate,
            "tenure": tenure,
            "monthly_installment": round(monthly_installment, 2)
        }

        return Response(response_data, status=status.HTTP_200_OK)

class CreateLoanView(APIView):
    def post(self, request):
        customer_id = request.data.get('customer_id')
        loan_amount = request.data.get('loan_amount')
        interest_rate = request.data.get('interest_rate')
        tenure = request.data.get('tenure')

        if not all([customer_id, loan_amount, interest_rate, tenure]):
            return Response({"error": "All fields are required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            customer = Customer.objects.get(customer_id=customer_id)
        except Customer.DoesNotExist:
            return Response({"error": "Customer not found"}, status=status.HTTP_404_NOT_FOUND)

        eligibility_response = CheckEligibilityView().post(request)

        if eligibility_response.data['approval']:
            loan = Loan.objects.create(
                customer=customer,
                loan_amount=loan_amount,
                tenure=tenure,
                interest_rate=eligibility_response.data['corrected_interest_rate'],
                monthly_repayment=eligibility_response.data['monthly_installment'],
                emis_paid_on_time=0,
                start_date=date.today(),
                end_date=date.today() + relativedelta(months=tenure)
            )
            response_data = {
                "loan_id": loan.loan_id,
                "customer_id": customer_id,
                "loan_approved": True,
                "message": "Loan approved",
                "monthly_installment": eligibility_response.data['monthly_installment']
            }
            return Response(response_data, status=status.HTTP_201_CREATED)
        else:
            response_data = {
                "loan_id": None,
                "customer_id": customer_id,
                "loan_approved": False,
                "message": "Loan not approved based on eligibility check",
                "monthly_installment": None
            }
            return Response(response_data, status=status.HTTP_200_OK)

class ViewLoanView(APIView):
    def get(self, request, loan_id):
        try:
            loan = Loan.objects.get(loan_id=loan_id)
        except Loan.DoesNotExist:
            return Response({"error": "Loan not found"}, status=status.HTTP_404_NOT_FOUND)

        customer_data = {
            "id": loan.customer.customer_id,
            "first_name": loan.customer.first_name,
            "last_name": loan.customer.last_name,
            "phone_number": loan.customer.phone_number,
            "age": loan.customer.age
        }

        response_data = {
            "loan_id": loan.loan_id,
            "customer": customer_data,
            "loan_amount": loan.loan_amount,
            "interest_rate": loan.interest_rate,
            "monthly_installment": loan.monthly_repayment,
            "tenure": loan.tenure
        }

        return Response(response_data, status=status.HTTP_200_OK)

class ViewLoansByCustomerView(APIView):
    def get(self, request, customer_id):
        try:
            customer = Customer.objects.get(customer_id=customer_id)
        except Customer.DoesNotExist:
            return Response({"error": "Customer not found"}, status=status.HTTP_404_NOT_FOUND)

        loans = Loan.objects.filter(customer=customer)
        
        response_data = []
        for loan in loans:
            repayments_left = loan.tenure - loan.emis_paid_on_time
            response_data.append({
                "loan_id": loan.loan_id,
                "loan_amount": loan.loan_amount,
                "interest_rate": loan.interest_rate,
                "monthly_installment": loan.monthly_repayment,
                "repayments_left": repayments_left
            })

        return Response(response_data, status=status.HTTP_200_OK)


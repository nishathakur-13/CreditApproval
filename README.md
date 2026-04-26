# Credit Approval System

This project is a Django-based credit approval system that provides a RESTful API for managing customers, checking loan eligibility, and creating loans. The system uses a credit scoring model to determine loan eligibility and leverages Celery for asynchronous data ingestion.

## Features

*   **Customer Registration:** Register new customers with their personal and financial details.
*   **Data Ingestion:** Asynchronously ingest customer and loan data from CSV files.
*   **Loan Eligibility Check:** Determine if a customer is eligible for a loan based on a credit scoring model.
*   **Loan Creation:** Create new loans for eligible customers.
*   **Loan Viewing:** View details of a specific loan or all loans for a particular customer.
*   **Containerized:** The entire application is containerized using Docker for easy setup and deployment.

## Technologies Used

*   **Backend:** Django, Django REST Framework
*   **Database:** PostgreSQL
*   **Asynchronous Tasks:** Celery, Redis
*   **Containerization:** Docker, Docker Compose

## Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/your-username/credit-approval-system.git
    cd credit-approval-system
    ```

2.  **Build and run the containers:**
    ```bash
    docker-compose up --build
    ```

3.  **Apply database migrations:**
    In a separate terminal, run the following command:
    ```bash
    docker-compose exec web python manage.py migrate
    ```

## Usage

Once the application is running, you can interact with the API at `http://localhost:8000/api/`.

### Data Ingestion

To ingest the initial customer and loan data, make a GET request to the following endpoint:

```
GET /api/ingest-data/
```

This will trigger asynchronous tasks to read the `customer_data.csv` and `loan_data.csv` files and populate the database.

## API Endpoints

| Method | Endpoint                        | Description                               |
| ------ | ------------------------------- | ----------------------------------------- |
| `POST` | `/api/register/`                | Register a new customer.                  |
| `GET`  | `/api/ingest-data/`             | Ingest customer and loan data.            |
| `POST` | `/api/check-eligibility/`       | Check loan eligibility for a customer.    |
| `POST` | `/api/create-loan/`             | Create a new loan.                        |
| `GET`  | `/api/view-loan/<loan_id>/`     | View details of a specific loan.          |
| `GET`  | `/api/view-loans/<customer_id>/`| View all loans for a specific customer.   |

### Example Requests

#### Register a new customer

```bash
curl -X POST http://localhost:8000/api/register/ \
-H "Content-Type: application/json" \
-d '{
    "first_name": "John",
    "last_name": "Doe",
    "age": 30,
    "monthly_income": 50000,
    "phone_number": "1234567890"
}'
```

#### Check loan eligibility

```bash
curl -X POST http://localhost:8000/api/check-eligibility/ \
-H "Content-Type: application/json" \
-d '{
    "customer_id": 1,
    "loan_amount": 100000,
    "interest_rate": 10,
    "tenure": 12
}'
```

#### Create a new loan

```bash
curl -X POST http://localhost:8000/api/create-loan/ \
-H "Content-Type: application/json" \
-d '{
    "customer_id": 1,
    "loan_amount": 100000,
    "interest_rate": 10,
    "tenure": 12
}'
```
# Brightloop -- Subscription Management System

A web-based subscription management platform designed to manage
customers, products, subscription plans, quotations, recurring invoices,
payments, discounts, and business operations from one workspace.

## Live Demo

**Frontend:** <https://odoosubsciptionmanagement.vercel.app/>

**Test User:**admin@brightlight.demo
**Password:**Admin@Brightlight2026!

## Overview

Brightloop provides a central place for a business to manage
subscription-related workflows. It supports role-based access for
administrators, staff, and customers, with access to relevant sections
based on the signed-in user's role.

The system is intended to make subscription operations easier to track,
reduce repetitive manual work, and keep important business records
connected.

## Key Features

-   **Authentication and roles:** Sign-in and customer registration,
    with admin, staff, and customer roles.
-   **Customer management:** Maintain customer billing and contact
    information.
-   **Staff management:** Allow administrators to manage staff accounts.
-   **Product management:** Create and manage products, including
    product type and pricing.
-   **Subscription plans:** Configure billing intervals, prices, minimum
    quantities, availability, and subscription options.
-   **Quotation templates:** Create reusable quotation templates with
    product line items and validity periods.
-   **Quotations:** Prepare and manage customer quotations.
-   **Subscription lifecycle:** Manage subscription records and
    supported actions such as confirmation, activation, pause, resume,
    renewal, and closure.
-   **Invoices:** View invoices, confirm or cancel eligible invoices,
    and download invoice PDFs.
-   **Payments:** Record payments and view payment-related information.
    Online payment checkout can be configured with Razorpay.
-   **Discounts and taxes:** Configure discount rules and tax rates.
-   **Dashboard and reports:** View business summaries and monthly
    collection information.

Some actions are restricted by role and by the current record status.

## Technology Stack

  Layer                Technologies
  -------------------- -----------------------------------------------
  Frontend             Next.js, React, TypeScript, Tailwind CSS
  Backend              Python, FastAPI
  Database             PostgreSQL
  ORM and migrations   SQLAlchemy, Alembic
  Frontend hosting     Vercel
  Backend hosting      Render
  Online payments      Razorpay integration (requires configuration)
  Email delivery       Resend integration (requires configuration)

## Application Architecture

``` text
                         ┌──────────────────────────┐
                         │       User / Browser     │
                         └────────────┬─────────────┘
                                      │
                                      ▼
                         ┌──────────────────────────┐
                         │     Next.js Frontend     │
                         │          Vercel          │
                         └────────────┬─────────────┘
                                      │ HTTPS API requests
                                      ▼
                         ┌──────────────────────────┐
                         │      FastAPI Backend     │
                         │          Render          │
                         └────────────┬─────────────┘
                                      │
                                      ▼
                         ┌──────────────────────────┐
                         │       PostgreSQL         │
                         └──────────────────────────┘

                    Optional external integrations:
                         Razorpay • Resend
```

## User Roles

  -----------------------------------------------------------------------
  Role                                Intended access
  ----------------------------------- -----------------------------------
  Admin                               Administrative operations, staff
                                      management, configuration, and
                                      business records

  Staff                               Day-to-day customer, product,
                                      quotation, subscription, and
                                      billing operations permitted by the
                                      application

  Customer                            Customer-facing subscription,
                                      quotation, invoice, payment, and
                                      profile information
  -----------------------------------------------------------------------

The backend must enforce authorization for protected operations; hiding
a frontend control alone is not a security boundary.

## Getting Started

### Prerequisites

Install the following before running the project locally:

-   Node.js and npm
-   Python 3.11 or a version supported by the backend dependencies
-   PostgreSQL database
-   Git

### 1. Clone the repository

``` bash
git clone <YOUR_GITHUB_REPOSITORY_URL>
cd <YOUR_REPOSITORY_FOLDER>
```

Replace the placeholders with your actual GitHub repository URL and
folder name.

### 2. Configure the backend

Open the backend directory:

``` bash
cd backend
```

Create and activate a virtual environment.

**Windows PowerShell:**

``` powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

**macOS / Linux:**

``` bash
python -m venv .venv
source .venv/bin/activate
```

Install the backend dependencies using the dependency file present in
the backend directory. For example, if the project contains
`requirements.txt`:

``` bash
pip install -r requirements.txt
```

Create a backend `.env` file using the variable names expected by the
backend settings. At minimum, configure the PostgreSQL connection string
and a strong, private application secret. Check the project's
settings/configuration file for the exact variable names and required
values.

Example only --- adapt the names to the backend configuration:

``` env
DATABASE_URL=postgresql://USER:PASSWORD@HOST:PORT/DATABASE
SECRET_KEY=replace-with-a-long-random-secret
```

Do not commit `.env` files or real credentials to Git.

### 3. Run database migrations

With the backend virtual environment active and the database configured:

``` bash
alembic upgrade head
```

If the project includes a seed script and you want sample data in a
development database, run the seed command documented by that script. Do
not run seed scripts against a production database unless you understand
the records they create.

### 4. Start the backend

From the backend directory, run:

``` bash
uvicorn app.main:app --reload --port 8000
```

The API should be available at:

-   API base: `http://localhost:8000`
-   Swagger documentation: `http://localhost:8000/docs`

### 5. Configure and start the frontend

Open a second terminal and navigate to the frontend directory:

``` bash
cd frontend
```

Install dependencies:

``` bash
npm install
```

Create the frontend environment file (commonly `.env.local`) and set the
API base URL using the exact environment variable read by
`src/lib/api.ts`.

For example, if the frontend uses `NEXT_PUBLIC_API_URL`:

``` env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

Start the frontend:

``` bash
npm run dev
```

Open <http://localhost:3000>.

> Environment variable names must match the code in
> `frontend/src/lib/api.ts`. Restart the Next.js development server
> after changing environment variables.

## Deployment Configuration

### Frontend (Vercel)

Configure the frontend environment variable in the Vercel project
settings. The variable name must match the one used by the frontend API
client.

Example:

``` env
NEXT_PUBLIC_API_URL=https://odoo-subscription-management.onrender.com
```

Apply the variable to the required environments (Production and
Preview), then redeploy the frontend so the updated value is included in
the build.

A `NEXT_PUBLIC_` variable is exposed to the browser. It is appropriate
for a public API base URL, but **never** use this prefix for passwords,
API secrets, database credentials, or private tokens.

### Backend (Render)

Configure the backend environment variables in the Render service
settings. Use the production PostgreSQL connection string, a strong
secret key, and the CORS origins required by the deployed frontend.

The backend CORS allowlist should contain the exact deployed frontend
origin, for example:

``` text
https://odoosubsciptionmanagement.vercel.app
```

Do not add a trailing slash to an origin in the CORS allowlist unless
the backend configuration specifically requires it.

### Optional integrations

-   **Razorpay:** Configure test credentials first. Keep the key secret
    and webhook secret on the backend only. Never expose them through
    `NEXT_PUBLIC_` variables.
-   **Resend:** Configure the email API key and a verified sender
    address on the backend. Keep the API key private.

The exact environment variable names for optional integrations should be
taken from the backend configuration and deployment settings.

## API Documentation

When the backend is running, FastAPI's interactive API documentation is
available at:

``` text
http://localhost:8000/docs
```

The deployed API documentation is available at:

<https://odoo-subscription-management.onrender.com/docs>

Use the API documentation to inspect available routes, request schemas,
and response formats.

## Security Notes

-   Never commit `.env` files, database passwords, JWT secrets, payment
    secrets, or email API keys.
-   Rotate any credentials that have accidentally been exposed.
-   Keep payment verification and role authorization on the backend.
-   Use HTTPS for deployed frontend and backend communication.
-   Restrict CORS to trusted frontend origins.
-   Use Razorpay test mode while testing payment flows.

## Project Structure

The exact repository layout may differ, but the application is organized
around separate frontend and backend components:

``` text
.
├── backend/
│   ├── app/
│   ├── migrations/
│   ├── alembic.ini
│   └── ...
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   ├── components/
│   │   └── lib/
│   └── ...
└── README.md
```

## Current Deployment Links

  --------------------------------------------------------------------------------------------
  Resource                            URL
  ----------------------------------- --------------------------------------------------------
  Live application                    https://odoosubsciptionmanagement.vercel.app/

  Backend API                         https://odoo-subscription-management.onrender.com

  API documentation                   https://odoo-subscription-management.onrender.com/docs
  --------------------------------------------------------------------------------------------

## Contributing

1.  Fork the repository or create a feature branch.
2.  Make focused changes and keep the code readable.
3.  Test the affected frontend and backend workflows.
4.  Submit a pull request with a clear description of the changes.

## License

Add the license that applies to this repository. If no license has been
selected, the project should not be assumed to be open source for reuse.

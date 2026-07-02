> 🇧🇷 [Versão em português](README.ptbr.md)

# Credit Transaction Module

This module provides functionality to manage and query users' credit transactions.

## Endpoints

### GET /credit-transactions

Lists the authenticated user's transactions with pagination and filters.

**Query Parameters (optional):**

- `page`: Page number (default: 1)
- `limit`: Items per page (default: 10, maximum: 100)
- `type`: Transaction type (PURCHASE, USAGE, REFUND)
- `startDate`: Start date (ISO string format)
- `endDate`: End date (ISO string format)

**Example:**

```bash
GET /credit-transactions?page=1&limit=20&type=PURCHASE&startDate=2025-01-01T00:00:00.000Z
```

**Response:**

```json
{
  "data": [
    {
      "id": 1,
      "type": "PURCHASE",
      "amount": 100.5,
      "description": "Purchase of credits",
      "createdAt": "2025-09-14T12:00:00.000Z",
      "user": {
        "id": 1,
        "firstName": "João",
        "lastName": "Silva",
        "email": "joao@example.com"
      }
    }
  ],
  "meta": {
    "total": 1,
    "lastPage": 1,
    "currentPage": 1,
    "perPage": 10,
    "prev": null,
    "next": null
  }
}
```

### GET /credit-transactions/:id

Fetches a specific transaction by ID (admins only).

### GET /credit-transactions/admin/all

Lists all transactions from all users (admins only).

## Module Structure

```
credit-transaction/
├── credit-transaction.controller.ts    # REST controller
├── credit-transaction.service.ts       # Business logic
├── credit-transaction.module.ts        # Main module
├── dto/
│   └── credit-transaction-filter.dto.ts # Filter DTO
├── entities/
│   └── credit-transaction.entity.ts     # Transaction entity
└── models/
    └── credit-transaction.dto.ts        # Response DTO
```

## Features

- ✅ Paginated listing of transactions per user
- ✅ Filters by transaction type
- ✅ Filters by date range
- ✅ Inclusion of user data in each transaction
- ✅ Ordering by creation date (most recent first)
- ✅ Endpoints for admins to query specific transactions
- ✅ Automatic Swagger documentation

## Upcoming Implementations

- [ ] Endpoint for admins to list all transactions
- [ ] Additional filters (minimum/maximum amount)
- [ ] Report export in CSV/PDF
- [ ] Aggregated statistics by period
```
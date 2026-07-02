> 🇬🇧 [English version](README.md)

# Credit Transaction Module

Este módulo fornece funcionalidades para gerenciar e consultar transações de créditos dos usuários.

## Endpoints

### GET /credit-transactions

Lista as transações do usuário autenticado com paginação e filtros.

**Parâmetros de Query (opcionais):**

- `page`: Número da página (padrão: 1)
- `limit`: Itens por página (padrão: 10, máximo: 100)
- `type`: Tipo da transação (PURCHASE, USAGE, REFUND)
- `startDate`: Data inicial (formato ISO string)
- `endDate`: Data final (formato ISO string)

**Exemplo:**

```bash
GET /credit-transactions?page=1&limit=20&type=PURCHASE&startDate=2025-01-01T00:00:00.000Z
```

**Resposta:**

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

Busca uma transação específica por ID (apenas para admins).

### GET /credit-transactions/admin/all

Lista todas as transações de todos os usuários (apenas para admins).

## Estrutura do Módulo

```
credit-transaction/
├── credit-transaction.controller.ts    # Controlador REST
├── credit-transaction.service.ts       # Lógica de negócio
├── credit-transaction.module.ts        # Módulo principal
├── dto/
│   └── credit-transaction-filter.dto.ts # DTO para filtros
├── entities/
│   └── credit-transaction.entity.ts     # Entidade da transação
└── models/
    └── credit-transaction.dto.ts        # DTO de resposta
```

## Funcionalidades

- ✅ Listagem paginada de transações por usuário
- ✅ Filtros por tipo de transação
- ✅ Filtros por período de data
- ✅ Inclusão de dados do usuário em cada transação
- ✅ Ordenação por data de criação (mais recente primeiro)
- ✅ Endpoints para admins consultarem transações específicas
- ✅ Documentação Swagger automática

## Próximas Implementações

- [ ] Endpoint para admins listarem todas as transações
- [ ] Filtros adicionais (valor mínimo/máximo)
- [ ] Exportação de relatórios em CSV/PDF
- [ ] Estatísticas agregadas por período

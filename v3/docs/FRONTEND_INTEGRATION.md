# Frontend Integration Guide

## Overview

This guide provides frontend developers with complete examples for integrating with the v3 deck persistence API. The backend provides full CRUD (Create, Read, Update, Delete) support for deck persistence, allowing users to save, load, edit, and manage their deck collections.

For backend implementation details, see [BACKEND_API.md](BACKEND_API.md).

## Base URL

```
http://localhost:8000
```

## Endpoints

### 1. Save a New Deck

**Endpoint:** `POST /api/decks`

**Description:** Save a newly created deck to the database.

**Request Body:**
```json
{
  "deck": {
    "cards": [...],
    "format": "Standard",
    "archetype": "Aggro",
    "colors": ["R", "G"],
    "total_cards": 60
  },
  "name": "Red-Green Aggro",
  "description": "Fast aggressive deck with efficient creatures",
  "quality_score": 0.85,
  "improvement_notes": "### Suggestions: ..."
}
```

**Response:**
```json
{
  "success": true,
  "deck_id": "550e8400-e29b-41d4-a716-446655440000",
  "message": "Deck 'Red-Green Aggro' saved successfully",
  "error": null
}
```

**Usage Example (Frontend):**
```javascript
async function saveDeck(deck, name, description, qualityScore) {
  const response = await fetch('http://localhost:8000/api/decks', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      deck: deck,
      name: name,
      description: description,
      quality_score: qualityScore
    })
  });

  const result = await response.json();
  if (result.success) {
    console.log('Deck saved with ID:', result.deck_id);
    return result.deck_id;
  } else {
    console.error('Save failed:', result.error);
    return null;
  }
}
```

---

### 2. List Saved Decks

**Endpoint:** `GET /api/decks`

**Description:** Retrieve a list of all saved decks with optional filters.

**Query Parameters:**
- `format` (optional): Filter by format (e.g., "Standard", "Commander")
- `archetype` (optional): Filter by archetype (e.g., "Aggro", "Control")
- `limit` (optional): Maximum results to return (default: 100)
- `offset` (optional): Number of results to skip for pagination (default: 0)

**Example Request:**
```
GET /api/decks?format=Standard&limit=20
```

**Response:**
```json
{
  "success": true,
  "decks": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "name": "Red-Green Aggro",
      "description": "Fast aggressive deck with efficient creatures",
      "format": "Standard",
      "archetype": "Aggro",
      "colors": ["R", "G"],
      "total_cards": 60,
      "quality_score": 0.85,
      "improvement_notes": "...",
      "created_at": "2025-01-15T10:30:00",
      "updated_at": "2025-01-15T10:30:00"
    },
    {
      "id": "660e8400-e29b-41d4-a716-446655440111",
      "name": "Blue-White Control",
      "description": "Control deck with counters and removal",
      "format": "Standard",
      "archetype": "Control",
      "colors": ["U", "W"],
      "total_cards": 60,
      "quality_score": 0.78,
      "created_at": "2025-01-14T15:20:00",
      "updated_at": "2025-01-14T15:20:00"
    }
  ],
  "total": 2,
  "error": null
}
```

**Usage Example (Frontend):**
```javascript
async function listDecks(format = null, archetype = null) {
  let url = 'http://localhost:8000/api/decks?';
  if (format) url += `format=${format}&`;
  if (archetype) url += `archetype=${archetype}`;

  const response = await fetch(url);
  const result = await response.json();

  if (result.success) {
    return result.decks;
  } else {
    console.error('Failed to load decks:', result.error);
    return [];
  }
}
```

---

### 3. Get a Specific Deck

**Endpoint:** `GET /api/decks/{deck_id}`

**Description:** Retrieve full details of a specific deck by its ID.

**Example Request:**
```
GET /api/decks/550e8400-e29b-41d4-a716-446655440000
```

**Response:**
```json
{
  "success": true,
  "deck_id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "Red-Green Aggro",
  "description": "Fast aggressive deck with efficient creatures",
  "format": "Standard",
  "archetype": "Aggro",
  "colors": ["R", "G"],
  "total_cards": 60,
  "quality_score": 0.85,
  "improvement_notes": "...",
  "deck": {
    "cards": [
      {
        "card": {
          "id": "card-123",
          "name": "Lightning Bolt",
          "mana_cost": "{R}",
          "cmc": 1.0,
          "type_line": "Instant",
          "oracle_text": "Lightning Bolt deals 3 damage to any target."
        },
        "quantity": 4
      }
    ],
    "format": "Standard",
    "archetype": "Aggro",
    "colors": ["R", "G"],
    "total_cards": 60
  },
  "created_at": "2025-01-15T10:30:00",
  "updated_at": "2025-01-15T10:30:00",
  "error": null
}
```

**Usage Example (Frontend):**
```javascript
async function loadDeck(deckId) {
  const response = await fetch(`http://localhost:8000/api/decks/${deckId}`);
  const result = await response.json();

  if (result.success) {
    return result.deck;
  } else {
    console.error('Failed to load deck:', result.error);
    return null;
  }
}
```

---

### 4. Update an Existing Deck

**Endpoint:** `PUT /api/decks/{deck_id}`

**Description:** Update an existing deck's data and/or metadata.

**Request Body:**
```json
{
  "deck": {
    "cards": [...],
    "format": "Standard",
    "archetype": "Aggro",
    "colors": ["R", "G"],
    "total_cards": 60
  },
  "name": "Updated Red-Green Aggro",
  "description": "Improved aggressive strategy",
  "quality_score": 0.90,
  "improvement_notes": "..."
}
```

**Note:** All fields are optional. Only include the fields you want to update.

**Response:**
```json
{
  "success": true,
  "message": "Deck 550e8400-e29b-41d4-a716-446655440000 updated successfully",
  "error": null
}
```

**Usage Example (Frontend):**
```javascript
async function updateDeck(deckId, updatedDeck, newName = null) {
  const response = await fetch(`http://localhost:8000/api/decks/${deckId}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      deck: updatedDeck,
      name: newName
    })
  });

  const result = await response.json();
  if (result.success) {
    console.log('Deck updated successfully');
    return true;
  } else {
    console.error('Update failed:', result.error);
    return false;
  }
}
```

---

### 5. Delete a Deck

**Endpoint:** `DELETE /api/decks/{deck_id}`

**Description:** Delete a deck from the database.

**Example Request:**
```
DELETE /api/decks/550e8400-e29b-41d4-a716-446655440000
```

**Response:**
```json
{
  "success": true,
  "message": "Deck 550e8400-e29b-41d4-a716-446655440000 deleted successfully",
  "error": null
}
```

**Usage Example (Frontend):**
```javascript
async function deleteDeck(deckId) {
  const response = await fetch(`http://localhost:8000/api/decks/${deckId}`, {
    method: 'DELETE'
  });

  const result = await response.json();
  if (result.success) {
    console.log('Deck deleted successfully');
    return true;
  } else {
    console.error('Delete failed:', result.error);
    return false;
  }
}
```

---

## Frontend Integration Guide

### Recommended User Flow

1. **Building a Deck:**
   - User creates a deck via chat interface → receives deck object
   - "Save Deck" button appears
   - User clicks "Save Deck" → modal opens asking for name/description
   - Frontend calls `POST /api/decks` → receives deck_id
   - Show success message with option to view in deck library

2. **Deck Library Page:**
   - Page loads → call `GET /api/decks` to get all saved decks
   - Display decks in grid/table with filters for format and archetype
   - Each deck card shows: name, format, archetype, colors, card count, quality score
   - Click deck → navigate to deck detail page

3. **Deck Detail/Edit Page:**
   - Load deck using `GET /api/decks/{id}`
   - Display full decklist
   - "Edit Deck" button → loads deck into chat interface
   - User modifies via chat → "Save Changes" button
   - Frontend calls `PUT /api/decks/{id}` to update
   - "Delete Deck" button → confirmation modal → `DELETE /api/decks/{id}`

4. **Chat Interface Integration:**
   - Add "Load Deck" button to chat interface
   - Shows modal with saved decks (from `GET /api/decks`)
   - User selects deck → loads into chat as `existing_deck` parameter
   - Chat continues with deck modification flow

### UI Components Needed

1. **Save Deck Modal**
   - Input: Deck name (required)
   - Textarea: Description (optional)
   - Display: Auto-calculated quality score
   - Buttons: Save, Cancel

2. **Deck Library Page**
   - Filters: Format dropdown, Archetype dropdown, Search by name
   - Deck Grid/Table: Shows deck cards with preview info
   - Pagination: If total > limit

3. **Deck Detail Page**
   - Header: Deck name, format, archetype, colors
   - Decklist: Grouped by card type, sorted by CMC
   - Metadata: Quality score, created/updated dates
   - Actions: Edit, Delete, Export

4. **Load Deck Modal**
   - List of saved decks with search/filter
   - Click to load into current chat session

### Error Handling

All endpoints return a consistent error format:

```json
{
  "success": false,
  "message": "Error message",
  "error": "Detailed error information"
}
```

**Common Error Cases:**
- `404`: Deck not found (GET, PUT, DELETE)
- `500`: Server error (database issues, validation errors)
- `400`: Invalid request data (malformed deck object)

### Database Schema (For Reference)

```sql
CREATE TABLE decks (
    id TEXT PRIMARY KEY,              -- UUID
    name TEXT NOT NULL,               -- User-provided name
    description TEXT,                 -- Optional description
    format TEXT NOT NULL,             -- "Standard", "Commander", etc.
    archetype TEXT,                   -- "Aggro", "Control", etc.
    colors TEXT,                      -- JSON array: ["R", "G"]
    deck_data TEXT NOT NULL,          -- Full JSON-serialized Deck object
    quality_score REAL,               -- 0.0 to 1.0
    improvement_notes TEXT,           -- AI-generated suggestions
    total_cards INTEGER,              -- Deck size
    created_at TIMESTAMP,             -- Auto-generated
    updated_at TIMESTAMP,             -- Auto-updated
    user_id TEXT                      -- For future multi-user support
)
```

## Testing the API

You can test the endpoints using curl:

```bash
# List all decks
curl http://localhost:8000/api/decks

# Get specific deck
curl http://localhost:8000/api/decks/{deck_id}

# Save a deck
curl -X POST http://localhost:8000/api/decks \
  -H "Content-Type: application/json" \
  -d '{"deck": {...}, "name": "Test Deck"}'

# Update a deck
curl -X PUT http://localhost:8000/api/decks/{deck_id} \
  -H "Content-Type: application/json" \
  -d '{"deck": {...}, "name": "Updated Test Deck"}'

# Delete a deck
curl -X DELETE http://localhost:8000/api/decks/{deck_id}
```

## Notes

- All deck persistence is independent of the FSM workflow
- Decks are saved with complete metadata for easy browsing
- The `deck_data` field contains the full deck JSON for reconstruction
- Quality scores are preserved for later analysis/sorting
- The `user_id` field is reserved for future multi-user support

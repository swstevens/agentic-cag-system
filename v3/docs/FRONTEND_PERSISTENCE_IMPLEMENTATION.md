# Frontend Deck Persistence Implementation

## Overview

The FastHTML frontend has been updated to integrate with the new deck persistence API endpoints. Users can now save, load, edit, and delete decks through an intuitive web interface.

## What Was Implemented

### 1. Updated Chat Component

**File:** `v3/frontend/components/chat.py`

**Changes:**
- Added `has_deck` and `deck_id` parameters to `chat_component()`
- Added dynamic action buttons based on deck state:
  - **No deck loaded:** Shows "📚 My Decks" button
  - **New deck loaded:** Shows "💾 Save Deck" + "📚 My Decks" buttons
  - **Editing existing deck:** Shows "💾 Save Changes" + "📚 My Decks" buttons

**Button Behaviors:**
- "Save Deck" → Opens modal to name and describe deck
- "Save Changes" → Updates existing deck in database
- "My Decks" → Navigates to deck library page

### 2. New Deck Library Component

**File:** `v3/frontend/components/deck_library.py` (NEW)

**Features:**
- Grid layout displaying saved decks as cards
- Each deck card shows:
  - Deck name and description
  - Format and archetype badges
  - Color identity badges
  - Card count and quality score
  - Edit and Delete buttons
- Filter controls:
  - Format dropdown (Standard, Modern, Commander, etc.)
  - Archetype dropdown (Aggro, Control, Midrange, Combo)
  - Filter button to apply selections
- Empty state with call-to-action when no decks exist

**Functions:**
- `deck_card_item(deck)` - Renders individual deck card
- `deck_library_component(decks, format_filter, archetype_filter)` - Main library view

### 3. Updated Main App

**File:** `v3/frontend/app.py`

**Session State Changes:**
- Added `deck_id` field to track currently loaded deck
- Updated `render_content()` to pass deck state to chat component
- Added modal container for save dialog

**New Routes:**

#### `/decks` - Deck Library Page
- **Method:** GET
- **Query Params:** `format`, `archetype` (optional)
- **Description:** Displays grid of saved decks with filtering
- **Backend API:** `GET /api/decks`

#### `/deck/{deck_id}` - Load Deck for Editing
- **Method:** GET
- **Description:** Loads specific deck into chat interface for editing
- **Backend API:** `GET /api/decks/{deck_id}`
- **Updates Session:**
  - Sets `deck` and `deck_id`
  - Adds welcome message
  - Sets context (format, colors, archetype)

#### `/deck/save-modal` - Save Deck Modal
- **Method:** GET
- **Description:** Renders modal dialog for saving new deck
- **Form Fields:**
  - Deck name (required)
  - Description (optional)
  - Quality score (displayed, read-only)

#### `/deck/close-modal` - Close Modal
- **Method:** GET
- **Description:** Clears modal container

#### `/deck/save` - Save Deck Action
- **Method:** POST
- **Form Data:** `name`, `description`
- **Description:** Saves current deck to database
- **Backend API:** `POST /api/decks`
- **On Success:**
  - Updates session with `deck_id`
  - Shows success message with links to close or view library

#### `/deck/update` - Update Deck Action
- **Method:** POST
- **Description:** Updates existing deck in database
- **Backend API:** `PUT /api/decks/{deck_id}`
- **On Success:** Adds success message to chat

#### `/deck/{deck_id}` - Delete Deck
- **Method:** DELETE
- **Description:** Deletes deck and reloads library
- **Backend API:** `DELETE /api/decks/{deck_id}`
- **Confirmation:** Uses HTMX `hx-confirm` for user confirmation

## User Flows

### Flow 1: Build and Save New Deck

1. User builds deck via chat interface
2. Deck appears in left panel
3. "💾 Save Deck" button appears in chat area
4. User clicks "Save Deck"
5. Modal opens with form (name, description)
6. User fills form and clicks "Save"
7. Deck saved to database
8. Success message shows with options to:
   - Close modal and continue editing
   - View deck library

### Flow 2: Browse Saved Decks

1. User clicks "📚 My Decks" button
2. Navigates to `/decks` page
3. Sees grid of all saved decks
4. Can filter by format/archetype
5. Each deck card shows:
   - Name, description
   - Format, archetype, colors
   - Card count, quality score
   - Edit/Delete buttons

### Flow 3: Edit Existing Deck

1. User on deck library page
2. Clicks "✏️ Edit" on a deck card
3. Loads deck into chat interface
4. Chat shows: "Loaded deck: [name]. You can now modify it..."
5. User modifies deck via chat
6. "💾 Save Changes" button appears
7. User clicks "Save Changes"
8. Deck updated in database
9. Success message appears in chat

### Flow 4: Delete Deck

1. User on deck library page
2. Clicks "🗑️ Delete" on a deck card
3. Confirmation dialog appears (HTMX confirm)
4. User confirms deletion
5. Deck removed from database
6. Library page refreshes without deleted deck

## API Integration

All frontend routes communicate with backend API endpoints:

```
Frontend Route              Backend API Endpoint
---------------------------------------------
/decks (GET)               → GET /api/decks
/deck/{id} (GET)           → GET /api/decks/{id}
/deck/save (POST)          → POST /api/decks
/deck/update (POST)        → PUT /api/decks/{id}
/deck/{id} (DELETE)        → DELETE /api/decks/{id}
```

## Technical Details

### HTMX Integration

All deck persistence actions use HTMX for seamless updates without page reloads:

```html
<!-- Save Deck Button -->
<button hx-get="/deck/save-modal" hx-target="#modal">
  Save Deck
</button>

<!-- Delete Deck Button -->
<button
  hx-delete="/deck/{id}"
  hx-confirm="Are you sure?"
  hx-target="#main-content">
  Delete
</button>
```

### Session Management

Session state tracks:
- `deck`: Current deck data (dict)
- `deck_id`: UUID of loaded deck (str or None)
- `messages`: Chat history (list)
- `context`: Deck metadata for continuity (dict)

### Error Handling

All async API calls wrapped in try/except:
- Network errors → Display user-friendly error message
- HTTP errors → Extract error from response
- Unexpected errors → Generic error message with details

### Modal System

Simple modal overlay using HTMX:
- Modal content loaded into `<div id="modal">`
- Close modal → Replace with empty `<div id="modal">`
- Form submission → Replace modal with success/error message
- Escape/Cancel → Close modal

## Styling Requirements

The following CSS classes need to be defined (add to `static/styles.css`):

```css
/* Deck Actions */
.deck-actions { display: flex; gap: 10px; margin-bottom: 15px; }
.btn { padding: 8px 16px; border-radius: 4px; cursor: pointer; }
.btn-primary { background: #0066cc; color: white; }
.btn-secondary { background: #6c757d; color: white; }
.btn-danger { background: #dc3545; color: white; }
.btn-sm { padding: 4px 8px; font-size: 0.875rem; }

/* Modal */
.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.5);
                 display: flex; align-items: center; justify-content: center; }
.modal-content { background: white; padding: 20px; border-radius: 8px;
                 max-width: 500px; width: 90%; }
.modal-header { display: flex; justify-content: space-between; margin-bottom: 15px; }
.modal-close { background: none; border: none; font-size: 24px; cursor: pointer; }
.modal-actions { display: flex; gap: 10px; justify-content: flex-end; margin-top: 15px; }
.modal-form .form-group { margin-bottom: 15px; }
.form-input, .form-textarea { width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px; }

/* Deck Library */
.library-header { display: flex; justify-content: space-between; margin-bottom: 20px; }
.library-filters { margin-bottom: 20px; }
.filter-controls { display: flex; gap: 10px; align-items: center; }
.filter-select { padding: 6px; border-radius: 4px; }
.deck-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 20px; }
.deck-card { border: 1px solid #ddd; border-radius: 8px; padding: 15px; }
.deck-card-title { margin: 0 0 10px 0; }
.deck-card-description { color: #666; margin-bottom: 10px; }
.deck-badges { display: flex; gap: 5px; flex-wrap: wrap; margin-bottom: 10px; }
.deck-badge { padding: 4px 8px; background: #e9ecef; border-radius: 4px; font-size: 0.875rem; }
.color-badge { padding: 4px 8px; border-radius: 50%; font-weight: bold; }
.color-W { background: #f0f0e0; }
.color-U { background: #a3c9e8; }
.color-B { background: #bbb; }
.color-R { background: #f5b3b3; }
.color-G { background: #b3e5b3; }
.color-C { background: #ddd; }
.deck-stats { display: flex; gap: 10px; margin-bottom: 10px; color: #666; font-size: 0.875rem; }
.deck-card-actions { display: flex; gap: 8px; }

/* Success/Error Messages */
.success-message { color: green; }
.error-message { color: red; }
.info-text { color: #666; }
```

## Testing Checklist

- [ ] Save new deck with name and description
- [ ] Save deck without description (optional field)
- [ ] View saved decks in library
- [ ] Filter decks by format
- [ ] Filter decks by archetype
- [ ] Filter decks by both format and archetype
- [ ] Load existing deck for editing
- [ ] Modify loaded deck and save changes
- [ ] Delete deck (with confirmation)
- [ ] Cancel save deck modal
- [ ] Handle save error (backend down, invalid data)
- [ ] Handle load error (deck not found)
- [ ] Handle delete error
- [ ] Session persistence (deck stays loaded across chat messages)
- [ ] Navigate between chat and library without losing state

## Known Limitations

1. **Quality Score Extraction:** Currently tries to parse quality score from chat messages. Could be improved by storing it directly in session when deck is built.

2. **No Pagination:** Deck library shows all decks. For large collections, pagination should be added.

3. **No Search:** Library filters only by format/archetype. Text search by name would be useful.

4. **No Deck Preview:** Clicking a deck in the library immediately loads it for editing. A preview view would be nice.

5. **No Undo:** Once a deck is deleted, it's gone. Consider soft deletes or confirmation with preview.

## Future Enhancements

- Add deck export (text file, Arena format, MTGO format)
- Add deck import from text
- Add deck comparison tool
- Add deck statistics (mana curve visualization, color distribution pie chart)
- Add sorting options (by date, quality score, name)
- Add deck tags for better organization
- Add deck sharing (public/private decks, share links)
- Add deck versioning (history of changes)

## File Summary

### Modified Files
- `v3/frontend/components/chat.py` - Added deck action buttons
- `v3/frontend/app.py` - Added deck persistence routes

### New Files
- `v3/frontend/components/deck_library.py` - Deck library component
- `v3/docs/FRONTEND_PERSISTENCE_IMPLEMENTATION.md` - This file

### Required CSS (To Add)
- `v3/frontend/static/styles.css` - Add modal, deck library, and button styles

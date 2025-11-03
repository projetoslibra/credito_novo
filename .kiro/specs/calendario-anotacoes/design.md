# Design Document - Calendário de Anotações

## Overview

The "Calendário de Anotações" feature will be implemented as a new tab in the existing Libra Capital Credit Analysis Streamlit application. The feature provides a personal calendar interface where logged-in users can create, edit, and delete daily annotations that are persisted in the PostgreSQL database. The design maintains consistency with the existing dark theme visual identity and integrates seamlessly with the current application architecture.

## Architecture

### Integration Points

The calendar feature integrates with the existing application through:

1. **Main Navigation**: Added as a fourth tab alongside "Overview", "Detalhada", and "Workflow"
2. **Session Management**: Uses existing `st.session_state.user` for user identification
3. **Database Layer**: Leverages existing database connection functions (`get_conn()`, `run_exec()`, `run_query_df()`)
4. **Visual Theme**: Maintains the existing color scheme and styling patterns

### High-Level Flow

```
User Login → Main Menu → Calendar Tab → Month View → Date Selection → Annotation Modal → Save/Delete → Database Update → UI Refresh
```

## Components and Interfaces

### 1. Main Navigation Integration

**Location**: Main application routing section (lines 950-965 in Credito_Libra.py)

**Implementation**:
- Add fourth column to existing 3-column layout
- New button: "📅 Calendário" 
- Route to `calendario()` function when `st.session_state.tab == "Calendário"`

### 2. Calendar Display Component

**Function**: `render_calendar_grid(year, month, annotations_dict)`

**Responsibilities**:
- Generate HTML/CSS calendar grid for specified month
- Highlight dates with existing annotations using HARVEST_GOLD color
- Handle click events for date selection
- Maintain responsive design for desktop and tablet

**Visual Design**:
- 7-column grid (Sunday to Saturday)
- Each date cell: 40px height, clickable
- Highlighted dates: border or background in HARVEST_GOLD (#C66300)
- Current date: subtle highlight in SPACE_CADET (#042F3C)

### 3. Month Navigation Component

**Function**: `render_month_navigation(current_year, current_month)`

**Responsibilities**:
- Previous/Next month buttons
- Month/Year display
- Update session state for month changes
- Trigger calendar re-render

**Visual Design**:
- Centered header with month/year
- Arrow buttons (◀ ▶) on sides
- Consistent with existing button styling

### 4. Annotation Modal Component

**Function**: `render_annotation_modal(selected_date, existing_note)`

**Responsibilities**:
- Display text area for note input/editing
- Show save and delete buttons (when applicable)
- Handle form submission
- Provide user feedback via `st.toast()`

**Visual Design**:
- Modal-style container using `st.container()` or `st.expander()`
- Text area: minimum 3 rows, expandable
- Buttons: Save (primary), Delete (secondary, only when note exists)
- Consistent with existing form styling

### 5. Database Interface Component

**Functions**:
- `load_user_annotations(usuario, year, month)`
- `save_annotation(usuario, data, nota)`
- `delete_annotation(usuario, data)`

**Responsibilities**:
- Execute database queries using existing connection functions
- Handle INSERT/UPDATE logic for annotations
- Manage database transactions and error handling

## Data Models

### Database Schema

```sql
CREATE TABLE IF NOT EXISTS anotacoes_usuario (
    id SERIAL PRIMARY KEY,
    usuario VARCHAR(50) NOT NULL,
    data DATE NOT NULL,
    nota TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(usuario, data)
);

-- Index for performance
CREATE INDEX IF NOT EXISTS idx_anotacoes_usuario_lookup 
ON anotacoes_usuario(usuario, data);
```

### Data Flow

1. **Load Annotations**: Query database for user's annotations in current month
2. **Display Calendar**: Render calendar with highlighted dates
3. **User Interaction**: Capture date clicks and show annotation interface
4. **Save Operation**: 
   - If annotation exists: UPDATE existing record
   - If new annotation: INSERT new record
5. **Delete Operation**: DELETE record from database
6. **UI Update**: Refresh calendar display and show feedback

### Session State Management

```python
# New session state variables
if "calendar_year" not in st.session_state:
    st.session_state.calendar_year = datetime.now().year
if "calendar_month" not in st.session_state:
    st.session_state.calendar_month = datetime.now().month
if "selected_date" not in st.session_state:
    st.session_state.selected_date = None
if "show_annotation_modal" not in st.session_state:
    st.session_state.show_annotation_modal = False
```

## Error Handling

### Database Errors
- Connection failures: Display user-friendly error message
- Query failures: Log error and show generic failure message
- Transaction rollback: Automatic via existing connection handling

### User Input Validation
- Empty annotations: Allow saving (user may want to create placeholder)
- Date validation: Ensure valid date selection
- Text length: No explicit limit (TEXT field supports large content)

### UI Error States
- Loading states: Show spinner during database operations
- Network errors: Graceful degradation with retry options
- Session timeout: Redirect to login if user session invalid

## Testing Strategy

### Unit Testing Focus
- Database operations (save, load, delete annotations)
- Date calculation utilities
- User input validation functions

### Integration Testing
- Calendar rendering with real data
- Month navigation functionality
- Database transaction handling
- User session integration

### User Acceptance Testing
- Calendar navigation across months
- Annotation creation and editing workflow
- Visual consistency with existing application
- Responsive behavior on different screen sizes

## Implementation Considerations

### Performance Optimization
- Load only current month's annotations (not entire year)
- Use database indexes for efficient queries
- Minimize re-renders through proper state management

### Security
- User isolation: All queries filtered by `st.session_state.user`
- SQL injection prevention: Use parameterized queries
- Session validation: Ensure valid user session before operations

### Accessibility
- Keyboard navigation support for calendar
- Screen reader compatibility
- High contrast mode support (already provided by dark theme)

### Responsive Design
- Calendar grid adapts to screen width
- Touch-friendly date selection on tablets
- Readable text sizes across devices

## Visual Design Specifications

### Color Scheme (Existing)
- Background: #061e26
- Text: HONEYDEW (#FFF4E3)
- Highlights: HARVEST_GOLD (#C66300)
- Secondary: SPACE_CADET (#042F3C)
- Muted: SLATE_GRAY (#717c89)

### Calendar-Specific Styling
```css
.calendar-grid {
    display: grid;
    grid-template-columns: repeat(7, 1fr);
    gap: 2px;
    background: #042F3C;
    border-radius: 8px;
    padding: 8px;
}

.calendar-cell {
    background: #061e26;
    border: 1px solid #104052;
    border-radius: 4px;
    height: 40px;
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    transition: all 0.2s ease;
}

.calendar-cell:hover {
    background: #0b2e39;
    border-color: #C66300;
}

.calendar-cell.has-annotation {
    border-color: #C66300;
    background: rgba(198, 99, 0, 0.1);
}

.calendar-cell.today {
    background: rgba(4, 47, 60, 0.5);
    font-weight: bold;
}
```

### Modal Styling
- Consistent with existing form containers
- Rounded corners and subtle shadows
- Proper spacing and typography hierarchy
- Clear visual separation between form elements

## Technical Implementation Notes

### Streamlit-Specific Considerations
- Use `st.rerun()` for UI updates after database operations
- Leverage `st.toast()` for user feedback
- Implement proper state management to prevent unnecessary re-renders
- Use `st.container()` or `st.columns()` for layout structure

### Database Integration
- Reuse existing connection pooling and error handling
- Follow established patterns for transaction management
- Maintain consistency with existing database interaction patterns

### Code Organization
- Single main function: `calendario(tipo, agente)`
- Helper functions for specific responsibilities
- Clear separation between UI rendering and business logic
- Consistent naming conventions with existing codebase
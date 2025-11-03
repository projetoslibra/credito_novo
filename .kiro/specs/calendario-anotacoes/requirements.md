# Requirements Document

## Introduction

This document specifies the requirements for adding a new "📅 Calendário de Anotações" tab to the Libra Capital Credit Analysis application. The feature will provide a personal notes calendar system where logged-in users can create, edit, and delete daily annotations that are persisted in the PostgreSQL database. The calendar will maintain the existing dark theme visual identity and integrate seamlessly with the current Streamlit application.

## Glossary

- **Calendar_System**: The new calendar tab module that manages user annotations
- **User_Session**: The current logged-in user identified by st.session_state.user
- **Annotation_Record**: A database record containing user notes for a specific date
- **Main_App**: The existing Credito_Libra.py Streamlit application
- **Database_Connection**: PostgreSQL connection using existing get_conn(), run_exec(), and run_query_df() functions
- **Visual_Theme**: The dark mode color scheme with #061e26 background, HONEYDEW text, HARVEST_GOLD highlights, and SPACE_CADET secondary tones

## Requirements

### Requirement 1

**User Story:** As a logged-in user, I want to access a calendar tab from the main menu, so that I can manage my personal daily annotations.

#### Acceptance Criteria

1. WHEN the user selects the calendar tab, THE Calendar_System SHALL display the monthly calendar view for the current month
2. THE Calendar_System SHALL integrate with the existing main menu navigation system
3. THE Calendar_System SHALL maintain the Visual_Theme consistency with the Main_App
4. THE Calendar_System SHALL display the header "📅 Calendário de Anotações Pessoais"
5. THE Calendar_System SHALL show the caption "Clique em um dia para adicionar ou editar suas anotações pessoais"

### Requirement 2

**User Story:** As a user, I want to navigate between different months in the calendar, so that I can view and manage annotations from past and future dates.

#### Acceptance Criteria

1. THE Calendar_System SHALL provide navigation controls to move to previous months
2. THE Calendar_System SHALL provide navigation controls to move to next months
3. WHEN the user navigates to a different month, THE Calendar_System SHALL update the calendar display accordingly
4. THE Calendar_System SHALL load and display existing annotations for the selected month

### Requirement 3

**User Story:** As a user, I want to see visual indicators on dates that have annotations, so that I can quickly identify which days contain my notes.

#### Acceptance Criteria

1. WHEN a date contains an Annotation_Record for the User_Session, THE Calendar_System SHALL display a visual highlight using HARVEST_GOLD color
2. THE Calendar_System SHALL distinguish between dates with annotations and dates without annotations
3. THE Calendar_System SHALL update visual indicators immediately after saving or deleting annotations

### Requirement 4

**User Story:** As a user, I want to click on any calendar date to create or edit annotations, so that I can manage my daily notes efficiently.

#### Acceptance Criteria

1. WHEN the user clicks on a calendar date, THE Calendar_System SHALL open an annotation input interface
2. IF an Annotation_Record exists for the selected date and User_Session, THEN THE Calendar_System SHALL display the existing note text
3. IF no Annotation_Record exists for the selected date and User_Session, THEN THE Calendar_System SHALL display an empty text input field
4. THE Calendar_System SHALL provide a text area for entering or editing annotation content

### Requirement 5

**User Story:** As a user, I want to save my annotations with visual feedback, so that I know my notes are successfully stored.

#### Acceptance Criteria

1. WHEN the user clicks the save button, THE Calendar_System SHALL persist the annotation to the Database_Connection
2. IF an Annotation_Record already exists for the User_Session and date, THEN THE Calendar_System SHALL update the existing record
3. IF no Annotation_Record exists for the User_Session and date, THEN THE Calendar_System SHALL create a new record
4. WHEN the save operation completes successfully, THE Calendar_System SHALL display "✅ Anotação salva com sucesso!" using st.toast
5. WHEN the save operation completes, THE Calendar_System SHALL refresh the calendar display

### Requirement 6

**User Story:** As a user, I want to delete my annotations when they are no longer needed, so that I can keep my calendar organized.

#### Acceptance Criteria

1. WHEN an Annotation_Record exists for a selected date, THE Calendar_System SHALL display a delete button
2. WHEN the user clicks the delete button, THE Calendar_System SHALL remove the Annotation_Record from the Database_Connection
3. WHEN the delete operation completes successfully, THE Calendar_System SHALL display appropriate feedback
4. WHEN the delete operation completes, THE Calendar_System SHALL refresh the calendar display

### Requirement 7

**User Story:** As a user, I want my annotations to be private and secure, so that only I can see and manage my personal notes.

#### Acceptance Criteria

1. THE Calendar_System SHALL only display Annotation_Records that belong to the current User_Session
2. THE Calendar_System SHALL filter all database queries by the User_Session identifier
3. THE Calendar_System SHALL prevent access to annotations from other users
4. THE Calendar_System SHALL require a valid User_Session to access any annotation functionality

### Requirement 8

**User Story:** As a system administrator, I want the calendar feature to use the existing database infrastructure, so that it integrates seamlessly with the current application architecture.

#### Acceptance Criteria

1. THE Calendar_System SHALL use the existing get_conn() function for database connections
2. THE Calendar_System SHALL use the existing run_exec() function for database write operations
3. THE Calendar_System SHALL use the existing run_query_df() function for database read operations
4. THE Calendar_System SHALL create the anotacoes_usuario table if it does not exist
5. THE Calendar_System SHALL handle database errors gracefully with appropriate rollback mechanisms

### Requirement 9

**User Story:** As a user, I want the calendar to be responsive and work on different screen sizes, so that I can use it on desktop and tablet devices.

#### Acceptance Criteria

1. THE Calendar_System SHALL display properly on desktop screen sizes
2. THE Calendar_System SHALL display properly on tablet screen sizes
3. THE Calendar_System SHALL maintain usability across different viewport dimensions
4. THE Calendar_System SHALL preserve the Visual_Theme consistency across all screen sizes
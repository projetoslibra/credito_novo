# Implementation Plan

- [ ] 1. Set up database schema and core infrastructure
  - Create the anotacoes_usuario table with proper indexes
  - Add database initialization to existing ensure_indexes() function
  - Implement database helper functions for annotation CRUD operations
  - _Requirements: 8.4, 8.5_

- [ ] 1.1 Create database table and indexes
  - Add CREATE TABLE IF NOT EXISTS statement for anotacoes_usuario
  - Create index for efficient user/date lookups
  - Integrate table creation into existing ensure_indexes() function
  - _Requirements: 8.4_

- [ ] 1.2 Implement annotation database operations
  - Create load_user_annotations(usuario, year, month) function
  - Create save_annotation(usuario, data, nota) function with INSERT/UPDATE logic
  - Create delete_annotation(usuario, data) function
  - Use existing run_query_df() and run_exec() functions
  - _Requirements: 5.2, 5.3, 6.2, 8.1, 8.2, 8.3_

- [ ] 2. Implement calendar display and navigation components
  - Create calendar grid rendering function
  - Implement month navigation controls
  - Add visual indicators for dates with annotations
  - Ensure responsive design for desktop and tablet
  - _Requirements: 1.1, 2.1, 2.2, 2.3, 3.1, 3.2, 9.1, 9.2, 9.3, 9.4_

- [ ] 2.1 Create calendar grid rendering function
  - Implement render_calendar_grid(year, month, annotations_dict) function
  - Generate HTML/CSS calendar layout with 7-column grid
  - Apply HARVEST_GOLD highlighting for dates with annotations
  - Handle date click events for annotation editing
  - _Requirements: 1.1, 3.1, 3.2, 4.1_

- [ ] 2.2 Implement month navigation controls
  - Create render_month_navigation(current_year, current_month) function
  - Add previous/next month buttons with proper state management
  - Display current month and year in header
  - Update calendar display when month changes
  - _Requirements: 2.1, 2.2, 2.3_

- [ ] 3. Create annotation input and editing interface
  - Implement annotation modal/form component
  - Add save and delete functionality with user feedback
  - Handle empty and existing annotation states
  - Integrate with database operations
  - _Requirements: 4.1, 4.2, 4.3, 4.4, 5.1, 5.4, 5.5, 6.1, 6.3, 6.4_

- [ ] 3.1 Implement annotation modal component
  - Create render_annotation_modal(selected_date, existing_note) function
  - Display text area for note input/editing
  - Show appropriate buttons based on annotation state (save always, delete when exists)
  - Handle form submission and user input validation
  - _Requirements: 4.1, 4.2, 4.3, 4.4_

- [ ] 3.2 Add save and delete operations with feedback
  - Implement save button functionality with database integration
  - Implement delete button functionality with database integration
  - Add st.toast() success messages for user feedback
  - Trigger UI refresh after successful operations using st.rerun()
  - _Requirements: 5.1, 5.4, 5.5, 6.1, 6.3, 6.4_

- [ ] 4. Integrate calendar tab with main application
  - Add calendar tab to main navigation menu
  - Create main calendario() function
  - Implement session state management for calendar
  - Ensure user privacy and data isolation
  - _Requirements: 1.2, 1.3, 1.4, 1.5, 7.1, 7.2, 7.3, 7.4_

- [ ] 4.1 Add calendar tab to main navigation
  - Modify main navigation section to include fourth column
  - Add "📅 Calendário" button with proper routing
  - Update tab routing logic to handle "Calendário" state
  - Maintain visual consistency with existing navigation
  - _Requirements: 1.2, 1.3_

- [ ] 4.2 Create main calendario function
  - Implement calendario(tipo, agente) function following existing pattern
  - Add proper header and caption as specified in requirements
  - Initialize session state variables for calendar functionality
  - Integrate all calendar components into cohesive interface
  - _Requirements: 1.1, 1.4, 1.5_

- [ ] 4.3 Implement user privacy and session management
  - Filter all database queries by st.session_state.user
  - Validate user session before allowing annotation operations
  - Ensure users can only access their own annotations
  - Add proper error handling for invalid sessions
  - _Requirements: 7.1, 7.2, 7.3, 7.4_

- [ ] 5. Apply visual styling and ensure responsive design
  - Implement calendar-specific CSS styling
  - Ensure visual consistency with existing dark theme
  - Test and optimize responsive behavior
  - Add proper hover and interaction states
  - _Requirements: 1.3, 9.1, 9.2, 9.3, 9.4_

- [ ] 5.1 Implement calendar-specific CSS styling
  - Create CSS classes for calendar grid, cells, and modal components
  - Apply HARVEST_GOLD highlighting for dates with annotations
  - Implement hover states and visual feedback
  - Ensure consistency with existing Visual_Theme
  - _Requirements: 1.3, 3.1, 3.2_

- [ ] 5.2 Optimize responsive design and accessibility
  - Test calendar display on desktop and tablet screen sizes
  - Ensure touch-friendly date selection on mobile devices
  - Verify text readability and contrast ratios
  - Test keyboard navigation support
  - _Requirements: 9.1, 9.2, 9.3, 9.4_

- [ ]* 6. Add comprehensive error handling and validation
  - Implement database error handling with user-friendly messages
  - Add input validation for annotation content
  - Handle edge cases and network failures gracefully
  - Add loading states during database operations
  - _Requirements: 8.5_

- [ ]* 7. Write unit tests for core functionality
  - Test database operations (save, load, delete annotations)
  - Test date calculation and calendar rendering utilities
  - Test user input validation functions
  - Test session management and user isolation
  - _Requirements: 7.1, 7.2, 7.3, 7.4_
# Redux State Management

This directory contains the Redux implementation for managing application state in the Insurance Report Generator app.

## Structure

- `index.js` - Configures and exports the Redux store
- `reportSlice.js` - Contains the report generation state slice with actions and reducers
- `hooks.js` - Provides typed hooks for accessing the Redux store

## Usage

### Accessing State

To access state in your components, use the custom hooks:

```jsx
import { useAppSelector, useAppDispatch } from '../store/hooks';

function MyComponent() {
  // Get values from Redux store
  const activeStep = useAppSelector(state => state.report.activeStep);
  const loading = useAppSelector(state => state.report.loading);
  
  // Get the dispatch function
  const dispatch = useAppDispatch();
  
  // ...rest of component
}
```

### Updating State

To update state, dispatch actions from the reportSlice:

```jsx
import { setActiveStep, setLoading } from '../store/reportSlice';

// In a component
const dispatch = useAppDispatch();

// Update step
dispatch(setActiveStep(2));

// Update loading state
dispatch(setLoading({ 
  isLoading: true, 
  progress: 50, 
  message: 'Processing...' 
}));
```

## State Structure

The report state includes:

```js
{
  activeStep: 0,            // Current step in the report generation process
  reportId: null,           // ID of the current report
  loading: {                // Loading state
    isLoading: false,       // Whether any loading operation is in progress
    progress: 0,            // Progress percentage (0-100)
    stage: 'initial',       // Current loading stage
    message: ''             // Message to display during loading
  },
  documentIds: [],          // IDs of uploaded documents
  content: null,            // Generated report content
  previewUrl: null,         // URL to preview the report
  error: null               // Error message, if any
}
```

## Migration Guide

When migrating existing components to use Redux:

1. Import the necessary hooks and actions
2. Replace useState calls with selectors and dispatch
3. Update event handlers to dispatch actions instead of calling setState

**Example:**

Before:
```jsx
const [activeStep, setActiveStep] = useState(0);
const handleNext = () => setActiveStep(activeStep + 1);
```

After:
```jsx
const dispatch = useAppDispatch();
const activeStep = useAppSelector(state => state.report.activeStep);
const handleNext = () => dispatch(setActiveStep(activeStep + 1));
```

## Adding New State

To add new state to the Redux store:

1. Update the initial state in reportSlice.js
2. Add new reducers for the state
3. Export the new actions
4. Use the new state and actions in your components 
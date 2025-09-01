# Flet Input Form Template

A web-based input form template built with Flet that demonstrates how to create forms with validation and send data to Kafka topics using Quix Streams. This template provides a foundation for developers to build data collection interfaces for their applications.

## Overview

This template showcases how to build interactive web forms with Flet that include:
- Form validation (required fields, numeric validation)
- Real-time data publishing to Kafka topics
- Status feedback and error handling
- Clean, responsive UI design

## How to run

Create a [Quix](https://portal.platform.quix.io/signup?xlink=github) account or log-in and visit the Samples to use this project.

Clicking `Edit code` on the Sample, forks the project to your own Git repo so you can customize it before deploying.

## Environment variables

The code sample uses the following environment variables:

- **output**: Name of the output topic to send form data to (default: "data-input")

## Form Components

This template includes examples of common form elements:

### Text Inputs
- Text fields with labels and hints
- Numeric input fields with validation
- Required field validation

### Dropdowns
- Selection dropdowns with predefined options
- Optional fields with default values

### Form Controls
- Submit button with click handling
- Form validation and error display
- Auto-clear functionality after successful submission

## Message Structure

The form generates structured JSON messages when submitted:

```json
{
  "field1": "text_value",
  "field2": 123.45,
  "field3": 67.89,
  "dropdown1": "selected_option",
  "dropdown2": "selected_mode",
  "timestamp": "2025-01-30T12:34:56.789Z",
  "source": "input-form"
}
```

## Key Features

- **Form Validation**: Client-side validation with clear error messages
- **Kafka Integration**: Direct publishing to Kafka topics via Quix Streams
- **Status Feedback**: Real-time connection and submission status
- **Error Handling**: Comprehensive error handling and user feedback
- **Responsive Design**: Clean UI that works across devices
- **Template Structure**: Easy to customize for different data collection needs

## Architecture

The template uses a singleton service pattern (`SharedQuixService`) to manage Kafka producer connections efficiently. This ensures:
- Single connection per application instance
- Consistent message delivery
- Proper resource management
- Easy integration across components

## Customization

To adapt this template for your use case:

1. **Modify Form Fields**: Update field definitions in `_initialize_form_fields()`
2. **Change Validation**: Customize validation logic in `_validate_required_fields()`
3. **Update Message Format**: Modify `_create_message_payload()` for your data structure
4. **Customize UI**: Adjust styling and layout in `setup_ui()`
5. **Configure Topics**: Set your Kafka topic via the `output` environment variable

## Dependencies

- **flet**: Web UI framework
- **quixstreams**: Kafka integration library
- **python-dotenv**: Environment variable management

## Contribute

Submit forked projects to the Quix [GitHub](https://github.com/quixio/quix-samples) repo. Any new project that we accept will be attributed to you and you'll receive $200 in Quix credit.

## Open source

This project is open source under the Apache 2.0 license and available in our [GitHub](https://github.com/quixio/quix-samples) repo.

Please star us and mention us on social to show your appreciation.
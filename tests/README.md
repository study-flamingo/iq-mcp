# IQ-MCP Test Suite

This directory contains comprehensive tests for the IQ-MCP Knowledge Graph Server, focusing on CRUD operations on the memory databank.

## Test Structure

### Core Test Files

- **`test_server_tools.py`** - Main test suite for all server tool functions
- **`test_integration.py`** - Integration tests for complete workflows
- **`conftest.py`** - Pytest fixtures and configuration
- **`pytest.ini`** - Pytest configuration settings

### Test Categories

#### Entity CRUD Tests
- Create entities (individual and batch)
- Delete entities (with cascade relation cleanup)
- Open/retrieve entities
- Input validation and error handling

#### Relation CRUD Tests
- Create relations between entities
- Delete relations
- Duplicate prevention
- JSON string and list input support

#### Observation CRUD Tests
- Add observations (string and temporal formats)
- Delete specific observations
- Group observations by durability type
- Mixed content type handling

#### Graph Operations Tests
- Read complete graph
- Search nodes by name, type, and content
- Cleanup outdated observations
- Empty graph handling

#### Error Handling Tests
- Invalid JSON input
- Missing required fields
- Non-existent entity references
- Empty parameter validation

#### Integration Tests
- Complete workflow scenarios
- Data persistence verification
- Concurrent operation handling
- Complex relationship modeling

## Running Tests

### Prerequisites

Ensure you have the development dependencies installed:

```bash
# Using uv (recommended)
uv sync --dev

# Or using pip
pip install -e ".[dev]"
```

### Basic Test Execution

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/test_server_tools.py

# Run specific test class
pytest tests/test_server_tools.py::TestEntityCRUD

# Run specific test method
pytest tests/test_server_tools.py::TestEntityCRUD::test_create_entities_list_input
```

### Test Categories

```bash
# Run only CRUD operation tests
pytest -m crud

# Run only unit tests
pytest -m unit

# Run only integration tests
pytest -m integration

# Exclude slow tests
pytest -m "not slow"
```

### Environment Configuration

Tests automatically use temporary memory files to avoid interfering with production data. You can also set a custom test memory path:

```bash
# Set custom test memory path
export MEMORY_FILE_PATH="/tmp/test_memory.jsonl"
pytest

# Or use inline environment variable
MEMORY_FILE_PATH="/tmp/test_memory.jsonl" pytest
```

## Test Features

### Isolated Test Environment
- Each test uses a temporary memory file
- No interference between tests
- Automatic cleanup after tests complete

### Comprehensive Coverage
- All server tool functions tested
- Both list and JSON string inputs supported
- Error conditions and edge cases covered
- Input validation thoroughly tested

### Real-world Scenarios
- Complete workflow testing
- Multi-entity relationship modeling
- Temporal observation handling
- Data persistence verification

### Async Test Support
- Full async/await support using pytest-asyncio
- Proper event loop management
- Concurrent operation testing

## Test Data

Tests use realistic sample data:

### Sample Entities
- **People**: Software engineers, managers, etc.
- **Organizations**: Companies, startups, etc.  
- **Projects**: Development projects with timelines

### Sample Relations$$
- **Employment**: "works at", "manages", "employs"
- **Project**: "leads", "develops", "sponsors"
- **Business**: "acquires", "collaborates with"

### Sample Observations
- **Permanent**: Birth dates, education, company founding
- **Long-term**: Job roles, addresses, project assignments
- **Short-term**: Current learning, project phases
- **Temporary**: Travel plans, current tasks

## Extending Tests

### Adding New Test Cases

1. **Create test method** in appropriate test class
2. **Use fixtures** for setup (manager, sample data)
3. **Test both success and error cases**
4. **Verify data persistence** if applicable

### Adding New Test Categories

1. **Create new test class** in existing file or new file
2. **Add appropriate markers** in pytest.ini
3. **Document purpose** and scope
4. **Ensure isolation** from other tests

### Testing Best Practices

- **Descriptive test names** that explain what is being tested
- **Arrange-Act-Assert** pattern in test structure
- **Test both positive and negative cases**
- **Use fixtures** for common setup
- **Clean up resources** appropriately
- **Assert meaningful conditions** not just execution

## Troubleshooting

### Common Issues

**Test file not found**

```bash
# Ensure you're in the project root
cd /path/to/iq-mcp
pytest
```

**Import errors**

```bash
# Install package in development mode
pip install -e .
```

**Permission errors with temp files**

```bash
# Check temp directory permissions
ls -la /tmp/
```

**Async test failures**

```bash
# Ensure pytest-asyncio is installed
pip install pytest-asyncio
```

### Debug Mode

Enable debug logging in tests:

```bash
# Set debug environment variable
export IQ_DEBUG=true
pytest -v -s
```

### Memory File Inspection

Examine test memory files for debugging:

```bash
# Run with custom memory path
MEMORY_FILE_PATH="/tmp/debug_memory.jsonl" pytest tests/test_server_tools.py::TestEntityCRUD::test_create_entities_list_input -v

# Inspect the memory file
cat /tmp/debug_memory.jsonl
```
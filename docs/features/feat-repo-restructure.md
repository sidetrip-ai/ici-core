# Repository Restructuring Specification

## Motivation

The current repository structure mixes user-facing and developer-focused content, which can create confusion for end users who just want to run the application. By reorganizing the repository, we aim to:

1. Make it simpler for users who only need to run the application
2. Provide a clear separation between user-facing elements and developer content
3. Organize code in a more maintainable and scalable way
4. Allow contributors to focus on specific areas of the codebase

## Current Structure

```
ici-core/
├── .git/
├── main.py                  # Entry point
├── db/                      # Database files
├── logs/                    # Log files
├── ici/                     # Main package
├── requirements.txt         # Dependencies
├── config.yaml              # Configuration
├── .env                     # Environment variables
├── tests/                   # Tests
├── pytest.ini               # Test configuration
├── setup.py                 # Package setup
├── examples/                # Example code
├── docs/                    # Documentation
├── README.md                # Repository info
├── changelog                # Change history
├── .gitignore               # Git ignore rules
├── ENV_VARIABLES.md         # Environment variable docs
├── LICENSE                  # License file
├── .cursor/                 # Editor config
├── .env.example             # Example env vars
└── .github/                 # GitHub configuration
```

## Proposed Structure

```
ici-core/
├── code/                     # All developer-focused content
│   ├── ici/                 # Main package
│   │   ├── adapters/
│   │   ├── core/
│   │   └── ...
│   ├── tests/              # Developer-focused: tests
│   ├── examples/           # Developer-focused: examples
│   └── docs/              # Developer documentation
│
├── db/                      # Database files/data in root for easy access
├── main.py                  # Main entry point for users
├── config.yaml             # Main configuration
├── .env.example            # Environment template
├── .env                    # Local environment (git-ignored)
├── README.md               # User-focused documentation
├── requirements.txt        # Dependencies
└── LICENSE                 # License file
```

## Technical Implementation Details

### 1. Directory Structure Changes

- Create a new `code/` directory at the root level
- Move `ici/`, `tests/`, `examples/`, and `docs/` into the `code/` directory
- Keep `db/`, `main.py`, `config.yaml`, `.env` files, and user-facing documentation in the root

### 2. Import Path Updates

#### Entry Point (main.py)

Current imports like:
```python
from ici.adapters.controller import command_line_controller
```

Will need to change to:
```python
from code.ici.adapters.controller import command_line_controller
```

#### Within Moved Packages

- **Relative imports** within the `ici` package may still work if they use relative paths
- **Absolute imports** will need updating:
  - `from ici.core import x` → `from code.ici.core import x`
  - `import ici.models` → `import code.ici.models`

#### Test Updates

- Update imports in test files to reference the new structure
- Update `pytest.ini` configuration if needed for test discovery

### 3. Path Reference Updates

- Review and update any code that references file paths:
```python
# Before
config_path = os.path.join(PROJECT_ROOT, 'config.yaml')

# After
config_path = os.path.join(PROJECT_ROOT, 'config.yaml')  # Unchanged if at root
```

- Database access paths:
```python
# Before
db_path = os.path.join(PROJECT_ROOT, 'db')

# After
db_path = os.path.join(PROJECT_ROOT, 'db')  # Unchanged if db stays at root
```

### 4. Package Configuration

- Update `setup.py` to reflect the new package structure:
```python
# Example update
packages=find_packages('code'),
package_dir={'': 'code'},
```

### 5. Documentation Updates

- Update any path references in documentation
- Create clear instructions for both users and developers
- Update any diagrams or visual representations of the codebase

## Migration Plan

### Phase 1: Preparation

1. Create backup/branch before making changes
2. Create the `code/` directory

### Phase 2: File Movement

1. Move `ici/` package to `code/ici/`
2. Move `tests/` to `code/tests/`
3. Move `examples/` to `code/examples/`
4. Move `docs/` to `code/docs/`

### Phase 3: Import and Path Updates

1. Update imports in `main.py`
2. Update imports within the moved packages
3. Update path references throughout the codebase
4. Update `setup.py` configuration

### Phase 4: Testing and Validation

1. Run tests to verify that the restructured code works
2. Manually test main functionality
3. Check that imports resolve correctly
4. Verify package installation still works

## Potential Challenges and Solutions

### Import Errors

**Challenge**: Moving packages can break import paths.
**Solution**: Systematic update of all import statements; use tools like `sed` or IDE refactoring features.

### Path Resolution Issues

**Challenge**: File paths that were hardcoded might break.
**Solution**: Consider implementing a utility function to get paths relative to the project root.

### Package Installation Problems

**Challenge**: Package installation might not work with the new structure.
**Solution**: Carefully update `setup.py` and test installation from both development and end-user perspectives.

### Developer Confusion

**Challenge**: Developers familiar with the old structure might be confused.
**Solution**: Clear documentation about the new structure in the README and developer guides.

## Benefits of New Structure

1. **User Experience**: Clean, simple structure at the root level for end users
2. **Developer Organization**: All development files in one place
3. **Maintainability**: Better separation of concerns
4. **Scalability**: Room for growth in organized structure
5. **Clarity**: Clear distinction between user and developer concerns

## Conclusion

This restructuring will create a more user-friendly and developer-friendly repository organization. By clearly separating user-facing content from developer-focused code, we make it easier for both groups to interact with the repository in appropriate ways.

The changes will require some short-term effort to update imports and paths, but the long-term benefits in maintainability and usability justify this investment. 
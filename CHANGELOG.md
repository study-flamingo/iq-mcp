# Changelog

All notable changes to the Enhanced Memory MCP Server with Temporal Observations will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.7.0] - 2025-06-26

### 🆕 Added
- **Temporal Observation System**: Observations now support timestamp and durability metadata
- **Durability Categories**: Four levels - permanent, long-term, short-term, temporary  
- **Smart Cleanup**: `cleanup_outdated_observations` tool for automatic removal of outdated information
- **Durability Querying**: `get_observations_by_durability` tool for categorized viewing
- **Enhanced TypeScript Interfaces**: 
  - `TimestampedObservation` interface for temporal observations
  - `ObservationInput` interface for flexible observation creation
- **Automatic Normalization**: Legacy string observations converted to temporal format on load
- **Mixed Format Support**: `add_observations` accepts both strings and temporal objects

### 🔄 Changed  
- **Enhanced `add_observations`**: Now supports temporal metadata while maintaining backward compatibility
- **Improved Error Handling**: Better error messages and type safety throughout
- **Updated Server Version**: Bumped to 0.7.0 to reflect temporal features
- **Comprehensive Documentation**: Updated README with temporal features and examples

### 🏗️ Technical Improvements
- **Type Safety**: Leveraged TypeScript string literal types for durability categories
- **Union Types**: Used for backward compatibility between string and temporal observations  
- **Helper Methods**: Added private methods for observation creation and normalization
- **Data Migration**: Automatic conversion of legacy JSONL format to temporal format

### 📚 Documentation
- **Updated README**: Comprehensive documentation of temporal features
- **API Reference**: Detailed documentation of all tools and their capabilities
- **Usage Examples**: Practical examples showing temporal observation usage
- **System Prompt**: Enhanced memory prompt template leveraging temporal features
- **TypeScript Examples**: Demonstrated modern TypeScript patterns and best practices

### 🔒 Backward Compatibility
- **Legacy Support**: All existing string observations continue to work
- **Default Behavior**: String observations default to "long-term" durability
- **Automatic Migration**: JSONL files automatically converted without data loss
- **API Compatibility**: All existing tool signatures remain unchanged

## [0.6.3] - Base Version

### Original Features from Anthropic MCP Memory Server
- Basic entity/relation/observation CRUD operations
- Simple string-based search functionality  
- JSONL storage format
- MCP protocol compliance
- Claude Desktop integration support

---

## Migration Guide

### From v0.6.3 to v0.7.0

**No action required!** The upgrade is fully backward compatible:

1. **Existing observations**: Automatically converted to temporal format with "long-term" durability
2. **Existing tools**: Continue to work exactly as before
3. **Data files**: Legacy JSONL files work without modification

**To leverage new features**:

```typescript
// Start using temporal observations
add_observations([{
  entityName: "user", 
  contents: [
    { content: "Permanent fact", durability: "permanent" },
    { content: "Current project", durability: "temporary" }
  ]
}])

// Clean up outdated information  
cleanup_outdated_observations()

// View observations by category
get_observations_by_durability("user")
```

## Acknowledgments

This enhanced version builds upon the excellent foundation provided by Anthropic's original MCP Memory Server. The temporal observation system was designed and implemented by the author as part of exploring advanced knowledge management patterns for AI assistants.

## Contributing

Contributions are welcome! Please feel free to submit issues and enhancement requests.

## License

MIT License - see [LICENSE](LICENSE) file for details.

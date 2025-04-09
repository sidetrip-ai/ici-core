# Effective Prompts for Working with ICI Core

This guide provides detailed prompts that you can use when interacting with AI assistants to help you work with the ICI Core framework. Copy and paste these prompts to get targeted assistance with understanding the codebase or developing custom components.

## Understanding the Codebase

```
I want to understand the ICI Core codebase architecture. Please explain:

1. The overall architecture and how components interact
2. The main data flow from ingestion to response generation
3. The purpose of each major component (Ingestor, Preprocessor, Embedder, Vector Store, Generator, etc.)
4. How configuration works via config.yaml
5. Which interfaces need to be implemented when creating custom components

Please reference specific files like core interfaces in ici/core/interfaces/ and example implementations in ici/adapters/ when explaining.
```

```
Please analyze the DefaultIngestionPipeline in ici/core/pipelines/default.py and explain how data flows through the ingestion process step by step. Show how the data is transformed from raw input to database storage.
```

## Building Custom Ingestors and Preprocessors

```
I want to build a custom ingestor and preprocessor for [XYZ] (replace with your specific data source like Twitter, Notion, Slack, etc.). 

For the ingestor:
1. Which interface must I implement? (Please reference ici/core/interfaces/ingestor.py)
2. What methods need to be implemented and what should each return?
3. How should I handle authentication with [XYZ]?
4. What's the expected format of the data I should return?
5. Where should I place my custom ingestor file?
6. How do I configure it in config.yaml?

For the preprocessor:
1. Which interface must I implement? (Please reference ici/core/interfaces/preprocessor.py)
2. How should I structure my preprocess method to convert [XYZ] data into standard documents?
3. What metadata should I include in each document?
4. How do I handle message grouping or chunking?
5. Where should I place my custom preprocessor file?
6. How do I configure it in config.yaml?

Please provide code examples that I can adapt.
```

```
I'm implementing a custom [XYZ] ingestor and I'm stuck on the retrieve_data method. I need to fetch [specific data type] from [XYZ API/data source]. Can you help me write this method with proper error handling and pagination? Here's what I have so far:

[paste your code here]
```

## Building a Custom Generator

```
I want to implement a custom Generator that uses [model/API of your choice, e.g., Claude, LLaMA, Gemini, etc.].

1. Please explain the Generator interface from ici/core/interfaces/generator.py
2. Walk me through how to implement the required initialize() and generate() methods
3. How should I handle token limits and context windows?
4. How do I integrate this with the prompt template system?
5. How do I configure authentication and API settings in config.yaml?
6. Where should I place my custom generator file?

Can you provide a code example with proper error handling and logging?
```

```
I'm building a custom Generator that needs to support streaming responses. How can I implement this functionality while adhering to the Generator interface? Please provide examples of how to:

1. Structure the generate() method to support streaming
2. Handle errors during generation
3. Configure stream parameters in config.yaml
```

## Debugging Common Issues

```
I'm encountering an error when running my ingestion pipeline with my custom [Component]. The error message is:

[paste error message here]

My implementation looks like:

[paste relevant code here]

How can I diagnose and fix this issue?
```

## Extending the System

```
I want to extend the ICI Core system to add [feature/functionality]. Which components should I modify or extend? Are there existing interfaces I should use? Please provide guidance on the best approach and reference relevant files in the codebase.
```

## Optimizing Performance

```
I'm experiencing performance issues with my [specific component, e.g., vector store, embedder, etc.]. The system is [describe issues, e.g., slow to respond, using excessive memory]. How can I optimize my implementation while still adhering to the required interfaces?
```

## Testing Components

```
How should I properly test my custom [Component Type]? Please provide examples of:

1. Unit tests for each method
2. Integration tests with other components
3. Approaches for mocking dependencies
4. Performance benchmarking

Please reference testing patterns used elsewhere in the codebase.
```

---

When using these prompts, replace the placeholders (text in brackets) with your specific details. For more information on each component, refer to the corresponding guide in the `docs/guides/` directory. 
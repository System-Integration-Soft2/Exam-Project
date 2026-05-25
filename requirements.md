Each group of students will use the programming language(s), framework(s), libraries, database(s), and testing tool(s) of their choice to develop 5 independent APIs with the following requirements:

The business scenario for each API will be chosen by the students

All APIs must interact with database-stored information. Use the database model(s) and management system(s) of your choice

All APIs must prevent SQL-injection, XSS, and CSRF

APIs to develop:

## REST

- Endpoints. At least:

    - 3 GET requests that retrieve several items

        - They must implement search and pagination

    - 3 GET requests that retrieve one item by ID

    - 1 POST request

    - 1 PUT request

    - 1 DELETE request

    - A login endpoint

    - A logout endpoint

- All mandatory RESTful constraints must be satisfied, including HATEOAS, which will provide contextual links

- The REST naming convention will be followed

- The API will be versioned. Use the format of your choice

- Authentication will be provided via OAuth2 with JWT

- Choose a revocation strategy and implement it using a key-value store

- OpenAPI documentation will be implemented

- A test suite in Postman or a similar tool will be provided

- It will include positive and negative requests

## SOAP

- Operations. At least:

    - 2 that read data

    - 2 that change data

- WSDL generation

- Inclusion of at least 2 faults for error handling

- A test suite in Postman or a similar tool will be provided

    - It will include positive and negative tests

## GraphQL

- At least:

    - 2 queries

    - 2 mutations

- SDL schema

- A test suite in Postman or a similar tool will be provided

    - It will include positive and negative tests

## gRPC

- At least:

    - 1 unary RPC

    - 1 bidirectional streaming RPC

- Protobuf generation

- A test suite in Postman or a similar tool will be provided

    - It will include positive and negative tests

## WebSockets

- The same unary and bidirectional streaming operations as in gRPC

- A test suite in Postman or a similar tool will be provided

    - It will include positive and negative tests
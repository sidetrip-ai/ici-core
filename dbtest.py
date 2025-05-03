import chromadb

client = chromadb.PersistentClient(path="./db/vector/chroma_db")

print(client.list_collections())




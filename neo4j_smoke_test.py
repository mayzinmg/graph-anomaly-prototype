import os
from neo4j import GraphDatabase

def get_required_env(name:str) -> str:
    value = os.getenv(name)
    if not value:
        raise ValueError(f"Environment variable '{name}' is required but not set.")
    return value

uri = get_required_env("NEO4J_URI")
user = get_required_env("NEO4J_USER")
password = get_required_env("NEO4J_PASSWORD")

def main()-> None:
    driver = GraphDatabase.driver(uri, auth=(user, password))
    try:
    
        with driver.session() as session:
            result = session.run("RETURN 1 AS number")
            record = result.single()
            print(f"Test query returned: {record['number']}")

    finally:
        driver.close()

if __name__ == "__main__":
    main()
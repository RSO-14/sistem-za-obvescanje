import os
import json
from db import get_organization_id_by_name, insert_or_update_event, insert_organization, create_tables
import glob

def main():
    data_folder = os.path.join(os.path.dirname(__file__), "mock-data")
    json_files = glob.glob(os.path.join(data_folder, "*.json"))

    for file_path in json_files:
        print(f"Obdelujem datoteko: {file_path}")
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

            org_name = data.get("organization_name")
            events = data.get("events", [])

            if not org_name:
                print(f"Manjka 'organization_name' v {file_path}")
                continue
            
            # Test
            insert_organization("Zavod za gozdove Slovenije")

            # Pridobi ID iz baze
            org_id = get_organization_id_by_name(org_name)

            if not org_id:
                print(f"Podjetje '{org_name}' ne obstaja v bazi.")
                continue

            print(f"Najden ID '{org_id}' za podjetje '{org_name}'")

            for event in events:
                event["organization_id"] = org_id
                insert_or_update_event(event)
                print(f"Dogodek '{event.get('headline')}' dodan/posodobljen.")

if __name__ == "__main__":
    create_tables()
    print("neki")
    main()
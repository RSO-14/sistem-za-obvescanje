from time import sleep
import requests
import xml.etree.ElementTree as ET
from db import create_tables, get_connection
from publisher import publish_event


BASE_URL = "https://meteo.arso.gov.si/uploads/probase/www/warning/text/sl/warning_SLOVENIA_{queried_location}_latest_CAP.xml"
LOCATIONS_ARRAY = ["SOUTH-WEST", "SOUTH-EAST", "MIDDLE", "NORTH-EAST", "NORTH-WEST"]

def fetch_warning_data(location: str) -> str:
    url = BASE_URL.format(queried_location=location)
    response = requests.get(url)
    response.raise_for_status()
    return response.text

def extract_area_from_headline(headline: str) -> str:
    if "/" not in headline:
        return None
    return headline.split("/")[-1].strip()

def parse_warning_data(data: str) -> dict:
    conn = get_connection()
    cursor = conn.cursor()
    try:
        # Define the namespace
        ns = {'cap': 'urn:oasis:names:tc:emergency:cap:1.2'}

        root = ET.fromstring(data)

        # Parse basic alert info
        identifier = root.find('cap:identifier', ns).text
        alert_info = {
            'identifier': identifier,
            'sender': root.find('cap:sender', ns).text,
            'sent': root.find('cap:sent', ns).text,
            'status': root.find('cap:status', ns).text,
        }

        # Parse info element
        for info in root.findall('cap:info', ns):
            if info is not None:
                language = info.find('cap:language', ns).text
                #event = info.find('cap:event', ns).text.split(" - ")[0]  # Get the part before " - "
                severity = info.find('cap:severity', ns).text
                urgency = info.find('cap:urgency', ns).text
                effective = info.find('cap:effective', ns).text
                onset = info.find('cap:onset', ns).text
                expires = info.find('cap:expires', ns).text
                certainty = info.find('cap:certainty', ns).text
                headline = info.find('cap:headline', ns).text
                description = info.find('cap:description', ns).text
                instruction = info.find('cap:instruction', ns).text

                # Parse parameters
                #parameters = {}
                event = "Unknown"
                for param in info.findall('cap:parameter', ns):
                    value_name = param.find('cap:valueName', ns).text
                    value = param.find('cap:value', ns).text
                    if value_name == "awareness_type":
                        event = value

                #print(parameters)

                alert_info[language] = alert_info[language] if language in alert_info else {}
                alert_info[language][event] = alert_info[language][event] if event in alert_info[language] else []
                alert_info[language][event].append({
                    'effective': effective,
                    'onset': onset,
                    'expires': expires,
                    'severity': severity,
                    'urgency': urgency,
                    'certainty': certainty,
                    'headline': headline,
                    'description': description,
                    'instruction': instruction
                })
                
                area = extract_area_from_headline(headline)

                cursor.execute("""
                    INSERT INTO alert_info (alert_identifier, language, event, effective, onset,
                                            expires, severity, urgency, certainty, headline,
                                            description, instruction, area)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) ON CONFLICT (alert_identifier, language, event, onset) DO NOTHING""",
                    (identifier, language, event, effective, onset,
                     expires, severity, urgency, certainty, headline,
                     description, instruction, area))

                conn.commit()
                
                if cursor.rowcount == 1 and language == "sl":
                    publish_event({
                        "identifier": identifier,
                        "language": language,
                        "event": event,
                        "effective": effective,
                        "onset": onset,
                        "expires": expires,
                        "severity": severity,
                        "urgency": urgency,
                        "certainty": certainty,
                        "headline": headline,
                        "description": description,
                        "instruction": instruction,
                        "area": area
                    })

        return alert_info

    except ET.ParseError as e:
        print(f"Error parsing XML: {e}")
        return {}
    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    create_tables()

    for location in LOCATIONS_ARRAY:
        try:
            data = fetch_warning_data(location)
            preprocessed_alert = parse_warning_data(data)
            print(preprocessed_alert)
            #print(f"Data for {location}:\n{data}\n")
        except requests.HTTPError as e:
            print(f"Failed to fetch data for {location}: {e}")

        sleep(2)

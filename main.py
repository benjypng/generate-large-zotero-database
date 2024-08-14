import os
import random
import sqlite3
import uuid
from datetime import datetime, timedelta

from faker import Faker

# Initialize Faker for generating random data
fake = Faker()

def random_date(start_date, end_date):
    return start_date + timedelta(
        seconds=random.randint(0, int((end_date - start_date).total_seconds()))
    )

def generate_random_item():
    item_type = random.choice(['book', 'journalArticle', 'webpage', 'report', 'thesis', 'conferencePaper'])
    key = str(uuid.uuid4()).replace('-', '')
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365*5)  # 5 years ago
    
    date_added = random_date(start_date, end_date)
    date_modified = random_date(date_added, end_date)
    access_date = random_date(date_added, end_date)
    
    item = {
        "key": key,
        "itemType": item_type,
        "title": fake.catch_phrase(),
        "abstractNote": fake.paragraph(),
        "language": fake.language_name(),
        "shortTitle": fake.word().capitalize(),
        "url": fake.url(),
        "accessDate": access_date.strftime("%Y-%m-%d %H:%M:%S"),
        "dateAdded": date_added.strftime("%Y-%m-%d %H:%M:%S"),
        "dateModified": date_modified.strftime("%Y-%m-%d %H:%M:%S"),
        "libraryCatalog": fake.company(),
        "extra": fake.sentence(),
        "version": random.randint(1, 10),
        "synced": random.choice([0, 1]),
        "creators": [{"creatorType": "author", "firstName": fake.first_name(), "lastName": fake.last_name()} for _ in range(random.randint(1, 3))]
    }
    
    if item_type == 'book':
        item.update({
            "publisher": fake.company(),
            "place": fake.city(),
            "date": fake.year(),
            "ISBN": fake.isbn13(),
            "numPages": str(random.randint(50, 1000)),
            "edition": f"{random.randint(1, 10)}th Edition",
            "series": fake.sentence(),
            "seriesNumber": str(random.randint(1, 20))
        })
    elif item_type == 'journalArticle':
        item.update({
            "publicationTitle": fake.sentence(),
            "volume": str(random.randint(1, 100)),
            "issue": str(random.randint(1, 12)),
            "pages": f"{random.randint(1, 100)}-{random.randint(101, 200)}",
            "date": fake.date_this_decade().strftime("%Y-%m-%d"),
            "ISSN": fake.isbn10(),
            "DOI": f"10.{random.randint(1000, 9999)}/{fake.md5()[:10]}",
            "journalAbbreviation": "".join(word[0].upper() for word in fake.words(3))
        })
    elif item_type == 'webpage':
        item.update({
            "websiteTitle": fake.company(),
            "websiteType": random.choice(["Blog", "Social Media", "News", "Academic"]),
            "date": fake.date_this_decade().strftime("%Y-%m-%d")
        })
    elif item_type in ['report', 'thesis']:
        item.update({
            "institution": fake.company(),
            "place": fake.city(),
            "date": fake.year(),
            "number": str(random.randint(1, 1000))
        })
    elif item_type == 'conferencePaper':
        item.update({
            "conferenceName": fake.catch_phrase(),
            "place": fake.city(),
            "date": fake.date_this_decade().strftime("%Y-%m-%d"),
            "proceedingsTitle": fake.sentence(),
            "DOI": f"10.{random.randint(1000, 9999)}/{fake.md5()[:10]}"
        })
    
    return item

def add_items_to_zotero(db_path, num_items=100):
    if not os.path.exists(db_path):
        print(f"Error: The file {db_path} does not exist.")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Start a transaction
        cursor.execute("BEGIN TRANSACTION")

        for _ in range(num_items):
            item = generate_random_item()
            
            # Insert into items table
            cursor.execute("""
                INSERT INTO items (itemTypeID, key, dateAdded, dateModified, clientDateModified, libraryID, version, synced)
                VALUES (
                    (SELECT itemTypeID FROM itemTypes WHERE typeName = ?),
                    ?, ?, ?, ?, 1, ?, ?
                )
            """, (item['itemType'], item['key'], item['dateAdded'], item['dateModified'], item['dateModified'], item['version'], item['synced']))
            
            item_id = cursor.lastrowid
            
            # Insert fields into itemData table
            for field, value in item.items():
                if field not in ['key', 'itemType', 'dateAdded', 'dateModified', 'clientDateModified', 'version', 'synced', 'creators']:
                    cursor.execute("""
                        INSERT OR IGNORE INTO itemDataValues (value) VALUES (?)
                    """, (str(value),))
                    
                    cursor.execute("""
                        INSERT INTO itemData (itemID, fieldID, valueID)
                        VALUES (?, (SELECT fieldID FROM fields WHERE fieldName = ?), 
                                   (SELECT valueID FROM itemDataValues WHERE value = ?))
                    """, (item_id, field, str(value)))
            
            # Insert creators
            for index, creator in enumerate(item['creators']):
                cursor.execute("""
                    INSERT INTO creators (firstName, lastName) VALUES (?, ?)
                """, (creator['firstName'], creator['lastName']))
                creator_id = cursor.lastrowid
                
                cursor.execute("""
                    INSERT INTO itemCreators (itemID, creatorID, creatorTypeID, orderIndex)
                    VALUES (?, ?, (SELECT creatorTypeID FROM creatorTypes WHERE creatorType = ?), ?)
                """, (item_id, creator_id, creator['creatorType'], index))

        # Commit the transaction
        conn.commit()
        print(f"Successfully added {num_items} items to the Zotero database.")

    except sqlite3.Error as e:
        print(f"An error occurred: {e}")
        conn.rollback()

    finally:
        conn.close()

# Usage
zotero_db_path = './zotero.sqlite'  # Replace with the actual path to your Zotero database
add_items_to_zotero(zotero_db_path, num_items=12000)

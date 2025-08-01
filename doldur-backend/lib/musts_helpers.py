import time
import requests
from lib.exceptions import RecoverException
from lib.constants import *
from lib.helpers import check_delay
import os
import json
from urllib.parse import urlparse, parse_qs
import logging

logger=logging.getLogger(consts.shared_logger)

def load_departments():
    """Find the departments JSON file from export_folder and return its contents as a dictionary."""
    file_path = os.path.join(consts.export_folder, consts.departments_out_name)
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            departments = json.load(file)
            return departments
    except Exception as e:
        logger.error(f"Failed to load departments from file {file_path}: {e}")
        return {}

def get_department_page(session: requests.Session, dept_code: str, tries: int = 10):
    """Fetch department catalog page using session with retry mechanism."""
    attempt = 0
    while attempt < tries:
        try:
            check_delay()
            response = session.get(
                consts.department_catalog_url.replace("{dept_code}", str(dept_code)), headers=consts.headers
            )
            response.encoding = "utf-8"

            if response.status_code == 200:
                return response
        except Exception as e:
            raise RecoverException("Request failed",{"dept_code":dept_code,"error":str(e)}) from None
        
        attempt += 1
    raise RecoverException("Failed to get department page", {"dept_code":dept_code,"trials":tries}) from None


def extract_course_code(course_link: str):
    """Extract the course code from a course URL."""
    try:
        parsed_url = urlparse(course_link)
        query_params = parse_qs(parsed_url.query)
        course_code = query_params.get("course_code", [None])[0]
        return course_code
    except Exception as e:
        raise RecoverException("Failed to extract course code",{"course_link":course_link,"error":str(e)}) from None

def extract_dept_node(dept_soup):
    """Extract department node data from BeautifulSoup object."""
    dept_node = {}
    try:
        semester_tables = dept_soup.find('div', {"class": "field-body"}).find_all('table')
        semester_tables = semester_tables[:-1]  # Skip the last table

        for sem_no, semester_table in enumerate(semester_tables,start=1):
            courses = []
            rows = semester_table.find_all('tr')
            if not rows:
                continue
            rows = rows[1:]  # Skip the header row

            for row in rows:
                cells = row.find_all('td')
                if not cells:
                    continue
                if len(cells) != 6:
                    break

                course_link = cells[0].find('a')
                if course_link:
                    course_link = course_link.get('href')
                    course_code = extract_course_code(course_link)
                    if course_code:
                        courses.append(course_code)

            if courses:
                dept_node[sem_no] = courses
    except Exception as e:
        raise RecoverException("Failed to extract the node",{"error":str(e)}) from None
    return dept_node

def write_musts(data:dict):
    data_path = os.path.join(consts.export_folder, consts.musts_out_name)
    try:
        with open(data_path, "w", encoding="utf-8") as data_file:
            json.dump(data, data_file, ensure_ascii=False, indent=4)
            return data_path
    except Exception as e:
        raise RecoverException("Failed to write musts",{"error":str(e)}) from None
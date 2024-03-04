# -*- coding:utf-8 -*-
from re import search, sub
from typing import Optional

from aiohttp import ClientError, ClientSession
from asyncache import cached
from bs4 import BeautifulSoup as Bs4
from cachetools import TTLCache

from .course import ALL_COURSE_CODE, Course, SimpleCourse

__CLASSROOM_STR_LIST = ["教室", "上課地點"]
__CLASSROOM_REGEX = (
    r"(?<=("
    + r"|".join(rf"(?<={name})" for name in __CLASSROOM_STR_LIST)
    + r")[:：為]).*?(?=$|[ .，。；【])"
)


def prase_title_field(data: Bs4) -> tuple[str, str, str, Optional[str]]:
    """
    Parse the title field from the given data.

    Args:
        data (Bs4): The BeautifulSoup data to parse.

    Returns:
        tuple[str, str, str, Optional[str]]: A tuple contain title, detail url, note, and location.
    """

    title = data.find("a").text.strip()
    detail_url = data.find("a").get("href")
    detail_url = "?" + detail_url.split("?")[1]

    if note := data.find("font").text[3:].strip():
        location = (
            sub(r"\s", " ", s.group())
            if (s := search(__CLASSROOM_REGEX, note))
            else None
        )

    return title, detail_url, note, location


def prase_teacher_field(data: Bs4) -> tuple[list[str], list[str]]:
    """
    Parses the teacher field from the given Bs4 data and returns two lists.

    Args:
        data (Bs4): The Bs4 data to parse.

    Returns:
        tuple[list[str], list[str]]: A tuple containing two lists,
        the first being a list of teacher names, and the second being a list of teacher links.
    """

    teachers = list[str]()
    teachers_url = list[str]()
    for teacher in data.find_all("a"):
        teachers.append(teacher.text)
        teachers_url.append("?" + teacher.get("href").split("?")[1])

    return teachers, teachers_url


def prase_time_location_filed(data: Bs4) -> tuple[list[str], list[str]]:
    """
    Parses the time and location fields from the given data.

    Args:
        data (Bs4): The BeautifulSoup data to parse.

    Returns:
        tuple[list[str], list[str]]: A tuple containing two lists, the first list
        containing the parsed times and the second list containing the parsed locations.
    """

    times = list[str]()
    locations = list[str]()
    for line_info in (str(line.text) for line in data.find_all("a")):
        if line_info.find("每週未維護") > -1:
            continue

        infos = line_info.split("\t", maxsplit=1)
        times.append(infos[0])
        if len(infos) > 1:
            locations.append(infos[1])

    return times, locations


class CourseRequest:
    __base_url = ""
    __URLS = [
        "http://120.126.197.7",
        "https://120.126.197.7",
        "https://sea.cc.ntpu.edu.tw",
    ]
    __COURSE_QUERY_URL = "/pls/dev_stud/course_query_all.queryByKeyword"
    COURSE_DICT = dict[str, SimpleCourse]()

    async def check_url(self, url: Optional[str] = None) -> bool:
        """
        Check if a given URL is accessible by sending a HEAD request to the URL.

        Args:
            url (str, optional): The URL to be checked. Defaults to base_url.

        Returns:
            bool: True if the URL is accessible, False otherwise.
        """

        if url is None:
            url = self.__base_url

        try:
            async with ClientSession() as session:
                async with session.head(url):
                    pass

        except ClientError:
            return False

        return True

    async def change_base_url(self) -> bool:
        """
        Check if a given URL is accessible. If not, try alternative URLs until a valid one is found.
        Returns True if a valid URL is found, False otherwise.
        """

        for url in self.__URLS:
            if await self.check_url(url):
                self.__base_url = url
                return True

        self.__base_url = ""
        return False

    @cached(TTLCache(maxsize=99, ttl=60 * 60 * 24))
    async def get_course_by_uid(self, uid: str) -> Optional[Course]:
        """
        Asynchronously retrieves a course by UID from the specified URL and returns a Course object if found, otherwise returns None.

        Args:
            uid (str): The unique identifier for the course.

        Returns:
            Optional[Course]: The Course object if found, otherwise None.
        """

        url = self.__base_url + self.__COURSE_QUERY_URL

        is_over_99 = len(uid) == 9
        year = int(uid[: 2 + is_over_99])
        term = int(uid[2 + is_over_99])
        courseno = uid[3 + is_over_99 :]

        params = {
            "qYear": year,
            "qTerm": term,
            "courseno": courseno,
            "seq1": "A",
            "seq2": "M",
        }

        try:
            async with ClientSession() as session:
                async with session.get(url, params=params) as res:
                    soup = Bs4(await res.text(errors="ignore"), "lxml")

            if table := soup.find("table"):
                course_infos = table.find("tbody").find("tr")
                course_field = course_infos.find_all("td")

                term = int(course_field[2].text)
                uid = course_field[3].text
                title, detail_url, note, location = prase_title_field(course_field[7])
                teachers, teachers_url = prase_teacher_field(course_field[8])
                times, locations = prase_time_location_filed(course_field[13])

                if location is not None:
                    locations.append(location)

                c = Course(
                    year=year,
                    term=term,
                    uid=uid,
                    title=title,
                    teachers=teachers,
                    times=times,
                    teachers_url=teachers_url,
                    locations=locations,
                    detail_url=detail_url,
                    note=note,
                )

                sc = super(Course, c)
                self.COURSE_DICT[str(sc)] = sc

                return c

        except ClientError:
            self.__base_url = ""

        return None

    async def get_simple_courses_by_year(
        self, year: int
    ) -> Optional[dict[str, SimpleCourse]]:
        """
        Asynchronously retrieves simple courses by year.

        Args:
            year (int): The year for which to retrieve the courses.

        Returns:
            Optional[dict[str, SimpleCourse]]: A dictionary of SimpleCourse objects, or None if an error occurs.
        """

        courses = dict[str, SimpleCourse]()
        url = self.__base_url + self.__COURSE_QUERY_URL

        for code in ALL_COURSE_CODE:
            params = {
                "qYear": year,
                "courseno": code,
                "seq1": "A",
                "seq2": "M",
            }

            try:
                async with ClientSession() as session:
                    async with session.get(url, params=params) as res:
                        soup = Bs4(await res.text(errors="ignore"), "lxml")

                if table := soup.find("table"):
                    course_infos = table.find("tbody").find_all("tr")
                    for course_info in course_infos:
                        course_field = course_info.find_all("td")

                        term = int(course_field[2].text)
                        uid = course_field[3].text
                        title = prase_title_field(course_field[7])[0]
                        teachers = prase_teacher_field(course_field[8])[0]
                        times = prase_time_location_filed(course_field[13])[0]

                        sc = SimpleCourse(
                            year=year,
                            term=term,
                            uid=uid,
                            title=title,
                            teachers=teachers,
                            times=times,
                        )

                        self.COURSE_DICT[str(sc)] = sc
                        courses[str(sc)] = sc

            except ClientError:
                self.__base_url = ""
                return None

        return courses


COURSE_REQUEST = CourseRequest()

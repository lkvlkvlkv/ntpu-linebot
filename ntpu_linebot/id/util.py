# -*- coding:utf-8 -*-
import random
from asyncio import sleep
from datetime import datetime
from enum import Enum, auto, unique
from typing import Optional

from aiohttp import ClientError, ClientSession
from sanic import Sanic

from .request import ID_REQUEST

# 科系名稱 -> 科系代碼
DEPARTMENT_CODE = {
    "法律": "71",
    "法學": "712",
    "司法": "714",
    "財法": "716",
    "公行": "72",
    "經濟": "73",
    "社學": "742",
    "社工": "744",
    "財政": "75",
    "不動": "76",
    "會計": "77",
    "統計": "78",
    "企管": "79",
    "金融": "80",
    "中文": "81",
    "應外": "82",
    "歷史": "83",
    "休運": "84",
    "資工": "85",
    "通訊": "86",
    "電機": "87",
}

# 科系全名 -> 科系代碼
FULL_DEPARTMENT_CODE = {
    "法律學系": "71",
    "法學組": "712",
    "司法組": "714",
    "財經法組": "716",
    "公共行政暨政策學系": "72",
    "經濟學系": "73",
    "社會學系": "742",
    "社會工作學系": "744",
    "財政學系": "75",
    "不動產與城鄉環境學系": "76",
    "會計學系": "77",
    "統計學系": "78",
    "企業管理學系": "79",
    "金融與合作經營學系": "80",
    "中國文學系": "81",
    "應用外語學系": "82",
    "歷史學系": "83",
    "休閒運動管理學系": "84",
    "資訊工程學系": "85",
    "通訊工程學系": "86",
    "電機工程學系": "87",
}

# 科系代碼 -> 科系名稱
DEPARTMENT_NAME = {v: k for k, v in DEPARTMENT_CODE.items()}

# 科系代碼 -> 科系全名
FULL_DEPARTMENT_NAME = {v: k for k, v in FULL_DEPARTMENT_CODE.items()}


# 學生資訊排序
@unique
class Order(Enum):
    """Enumeration representing the order in which different items should be displayed or sorted."""

    ID = auto()
    NAME = auto()
    YEAR = auto()
    DEPARTMENT = auto()
    FULL_DEPARTMENT = auto()


async def student_info_format(
    student_id: str,
    name: Optional[str] = None,
    order: Optional[list[Order]] = None,
    space: int = 1,
) -> str:
    """
    Format the student information based on the given parameters and return the formatted string.

    Args:
        student_id (str): The ID of the student
        name (str, optional): The name of the student. Defaults to None.
        order (list[Order], optional): The order in which the student information should be formatted. Defaults to None.
        space (int, optional): The space between the formatted information. Defaults to 1.

    Returns:
        str: The formatted student information.
    """

    # Get the student's name if not provided
    if name is None:
        name = await ID_REQUEST.get_student_by_id(student_id)

        if not name:
            return ""

    # Set default order if not provided
    if order is None:
        order = [Order.YEAR, Order.DEPARTMENT, Order.ID, Order.NAME]

    message = []
    is_over_99 = len(student_id) == 9

    # Format the student information based on the order
    for o in order:
        if o == Order.ID:
            message.append(student_id)
        elif o == Order.NAME:
            message.append(name)
        elif o == Order.YEAR:
            year = student_id[1 : is_over_99 + 3]
            message.append(year)
        elif o == Order.DEPARTMENT:
            department = student_id[is_over_99 + 3 : is_over_99 + 5]
            if department == DEPARTMENT_CODE["社學"][0:2]:
                department += student_id[is_over_99 + 5]

            message.append(DEPARTMENT_NAME[department] + "系")
        elif o == Order.FULL_DEPARTMENT:
            department = student_id[is_over_99 + 3 : is_over_99 + 5]
            if department in [DEPARTMENT_CODE["法律"], DEPARTMENT_CODE["社學"][:2]]:
                department += student_id[is_over_99 + 5]

            if department[0:2] == DEPARTMENT_CODE["法律"]:
                message.append("法律系")
                message.append(DEPARTMENT_NAME[department] + "組")
            else:
                message.append(DEPARTMENT_NAME[department] + "系")
        else:
            raise ValueError("Invalid order")

    # Join the formatted information with spaces and return
    return (" " * space).join(message)


async def healthz(app: Sanic) -> bool:
    """
    Asynchronous function to check the health of the application.

    Args:
        app (Sanic): The Sanic application.

    Returns:
        bool: True if the health check is successful, False otherwise.
    """

    try:
        async with ClientSession() as session:
            async with session.head(ID_REQUEST.base_url):
                pass

    except ClientError:
        if not await ID_REQUEST.change_base_url():
            return False

        await app.cancel_task("renew_student_list", raise_exception=False)
        app.add_task(renew_student_list, name="renew_student_list")

    return True


async def renew_student_list() -> None:
    """
	Asynchronously renews the student list for the current and previous five years for each department.
	"""

    cur_year = datetime.now().year - 1911
    for year in range(cur_year - 5, cur_year + 1):
        for dep in DEPARTMENT_CODE.values():
            await ID_REQUEST.get_students_by_year_and_department(str(year), str(dep))
            await sleep(random.uniform(5, 10))


def search_students_by_name(name: str) -> list[tuple[str, str]]:
    """
    Searches for students by name.

    Args:
        name (str): The name of the student to search for.

    Returns:
        list: A list of tuples containing the names and IDs of the matching students.
    """

    students = []
    for key, value in ID_REQUEST.STUDENT_DICT.items():
        if set(name).issubset(set(value)):
            students.append((key, value))

    return students


async def search_students_by_year_and_department(year: str, department: str) -> str:
    """
    Asynchronously search for students by year and department.

    Args:
        year (str): The year to search for.
        department (str): The department to search within.

    Returns:
        str: Information about the students found, including their IDs, names, and total count.
    """
    students = await ID_REQUEST.get_students_by_year_and_department(year, department)

    department_name = DEPARTMENT_NAME.get(department, "")
    department_type = "組" if department.startswith(DEPARTMENT_CODE["法律"]) else "系"

    if students:
        students_info = "\n".join(
            [
                await student_info_format(
                    student_id, student_name, [Order.ID, Order.NAME], 3
                )
                for student_id, student_name in students.items()
            ]
        )

        students_info += f"\n\n{year}學年度{department_name}{department_type}共有{len(students)}位學生"
    else:
        students_info = f"{year}學年度{department_name}{department_type}好像沒有人耶OAO"

    return students_info
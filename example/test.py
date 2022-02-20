from pprint import pprint
from typing import Optional, List, Union
from pydantic import BaseModel

from pierdolnik import Pierdolnik


app = Pierdolnik()


@app.route('/:title/:uid/params', http_methods=['GET', 'POST'])
def hemlo(title: str, uid: int, name: str, age: int = 0):
    if age:
        return f'{uid}: hemlo, {title} {name} of age {age}'
    return f'{uid}: hemlo, {title} {name}'


@app.route('/upload_file', http_methods=['POST'])
def upload_file(image: bytes):
    with open('image.png', 'wb') as file:
        file.write(image)


class Person(BaseModel):
    name: str
    age: Optional[int]


class Numbers(BaseModel):
    type: str
    values: List[Union[float, int]]


@app.route('/person', http_methods=['POST'])
def person_pydantic(person: Person):
    name = person.name
    age = person.age
    if age:
        return f'hemlo, {name} of age {age}'
    return f'hemlo, {name}'


@app.route('/person_and_numbers', http_methods=['POST'])
def person_and_numbers_pydantic(person: Person, numbers: Numbers):
    print(f'{numbers = }')
    name = person.name
    age = person.age
    if age:
        return f'hemlo, {name} of age {age}'
    return f'hemlo, {name}'


@app.route('/patch', http_methods=['PATCH'])
def patch():
    return 'patching something'


@app.route('/invalid_code', http_methods=['GET'])
def invalid_code():
    return 'invalid code', 600


app.less_go()
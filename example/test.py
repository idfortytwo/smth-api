from pprint import pprint
from typing import Optional, List, Union
from pydantic import BaseModel

from smthapi import SomethingAPI

app = SomethingAPI()


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


@app.route('/people', http_methods=['POST'])
def person_pydantic(people: List[Person]):
    for person in people:
        print(person)
    return 'works'


@app.route('/just_json', http_methods=['POST'])
def just_json(json_data):
    pprint(json_data, indent=4)
    return json_data


@app.route('/invalid_code', http_methods=['GET'])
def invalid_code():
    return 'invalid code', 600


app.less_go()
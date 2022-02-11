from pierdolnik import Pierdolnik


app = Pierdolnik()


@app.route('/:title/:uid/params', http_methods=['GET', 'POST'])
def hemlo(title: str, uid: int, name: str, age: int = 0):
    if age:
        return f'{uid}: hemlo, {title} {name} of age {age}'
    return f'{uid}: hemlo, {title} {name}'


@app.route('/poshel', http_methods=['GET'])
def poshel():
    return 'away with your football', 400


@app.route('/patch', http_methods=['PATCH'])
def patch():
    return 'patching something'


@app.route('/invalid_code', http_methods=['GET'])
def invalid_code():
    return 'invalid code', 600


app.less_go()
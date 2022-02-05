from pierdolnik import Pierdolnik

app = Pierdolnik()


@app.route('/', http_methods=['GET', 'POST'])
def hemlo():
    return 'hemlo'


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
# APIerdolnik

Minimalistic Python web framework - in development

## Features
- Parametrized routing
- Authomatic query, form, JSON and bytes parameter extraction
- Pydantic models integration and parameters validation
- Simple responses

## Examples
```python
from apierdolnik import APIerdolnik

app = APIerdolnik(host='localhost', port=8080)


# optional and required, positional and query params
@app.route('/:title/:uid/params', http_methods=['GET', 'POST'])
def hemlo(title: str, uid: int, name: str, age: int = 0):
    if age:
        return f'{uid}: hemlo, {title} {name} of age {age}'
    return f'{uid}: hemlo, {title} {name}'


# form data upload
@app.route('/upload_file', http_methods=['POST'])
def upload_file(image: bytes):
    with open('image.png', 'wb') as file:
        file.write(image)

        
app.less_go()
```
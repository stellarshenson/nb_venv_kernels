import json


async def test_hello(jp_fetch):
    # When
    response = await jp_fetch("nb-uv-kernels", "hello")

    # Then
    assert response.code == 200
    payload = json.loads(response.body)
    assert payload == {
            "data": (
                "Hello, world!"
                " This is the '/nb-uv-kernels/hello' endpoint."
                " Try visiting me in your browser!"
            ),
        }

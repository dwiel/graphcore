# graphcore
falcor + graphql + axpress

### example

```
import graphcore

testgraphcore = graphcore.Graphcore()

@testgraphcore.rule(['user.name'], 'user.abbreviation')
def user_name_to_abbreviation(name):
    return ''.join(part[0].upper() for part in name.split(' '))


@testgraphcore.rule(['user.id'], 'user.name')
def user_id_to_user_name(id):
    return 'John Bob Smith '+str(id)


def test_basic():
    testgraphcore.query({
        'user.id': 1,
        'user.abbreviation?': None,
    })
    
    self.assertEqual(ret, {'user.abbreviation': 'JBS1'})
```

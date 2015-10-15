# graphcore
falcor + graphql + axpress

### example

```
import graphcore

testgraphcore = graphcore.Graphcore()

@testgraphcore.input(('user.name',))
@testgraphcore.output('user.abbreviation')
def user_id_to_user_name(name):
    return ''.join(part[0].upper() for part in name.split(' ') )


@testgraphcore.input(('user.id',))
@testgraphcore.output('user.name')
def user_id_to_user_name(id):
    return 'John Bob Smith '+str(id)


def test_basic():
    testgraphcore.query({
        'user.id': 1,
        'user.abbreviation': graphcore.OutVar(),
    })
    
    self.assertEqual(ret, {'user.abbreviation': 'JBS1'})
```

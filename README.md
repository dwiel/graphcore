# graphcore
falcor + graphql + axpress

### example

```
import graphcore

testgraphcore = graphcore.Graphcore()

@testgraphcore.input(('users.id',))
@testgraphcore.output('users.name')
def user_id_to_user_name(id):
    return 'name_'+str(id)


def test_basic(self):
    testgraphcore.query({
        'users.id': 1,
        'users.name': graphcore.OutVar(),
    })
    
    self.assertEqual(ret, {'users.name': 'name_1'})
```

# AST

### Design Decisions

#### Option #1: QueryPlan start off with sequential list of rules (winner)

It seems a bit inefficient to build the rules first and then have to transform
them to an ast later.  A recursive backwards search starting from the unbound
clauses does not cleanly map to an ast, since it is possible that some of the
original unbound clauses will be necessary prerequists to other clauses and so
can not be assumed to be at the root of the ast.  It is still possible that a
recursive search will somehow make sense for some other reason, but it isnt
because the ast cleanly falls out of it.

It might actually turn out to morph into the recursive ast building, but thats
ok, no need to start there at the moment.

#### Option #2: QueryPlan build the ast from the get go

Does the QueryPlan even have enough information to do this?  Or does it need
the full list of rules first?  The list of rules right now is relatively
straightforward to reason about.  There is no recurisve search.  Maybe the
recursive search would be easier.  The recursive search would get rid of the
awkward unbound clause iterator which has to deal with the query changing
underneath of it.

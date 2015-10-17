# AST

### Design Decisions

#### Option #1: QueryPlan start off with sequential list of rules

It seems a bit inefficient to build the rules first and then have to transform
them to an ast later.

#### Option #2: QueryPlan build the ast from the get go

Does the QueryPlan even have enough information to do this?  Or does it need
the full list of rules first?  The list of rules right now is relatively
straightforward to reason about.  There is no recurisve search.  Maybe the
recursive search would be easier.  The recursive search would get rid of the
awkward unbound clause iterator which has to deal with the query changing
underneath of it.

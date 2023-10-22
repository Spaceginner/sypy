# sypy.

the barely working fastapi-inspired HTTP API server!1

## why?

~~why not?~~ i wanted to learn some stuff, and also i kinda didnt like the overhead of fastapi either (come on, 25
function calls to get to the callback? i know in my case it aint better really, the packet goes through... 3 queues
iirc? and also, `wrk` reports that in 1% of cases latency is like 1s :skull: and sometimes server doesnt even
respond(???))

## why dont you use xxx builtin lib or smth

i wanted to be (1) dependency-free (2) written in (as much as it goes) pure python from complete scratch

## ps

it is still in very WIP state, codebase is a mess, documentation is basically non-existant (only `example.py` lmfao) and
it may break sometimes

## license

its [gpl2](https://www.gnu.org/licenses/old-licenses/gpl-2.0.txt)

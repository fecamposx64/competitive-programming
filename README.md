# Competitive Programming

Personal C++ repository for competitive programming practice, with CSES solutions, ICPC/SBC contest material references, and local tooling for compilation and test execution.

## Scope

- Solve and organize problems from CSES and ICPC/SBC contests.
- Keep short, readable C++ solutions with predictable naming.
- Track algorithms, data structures, complexity, and common implementation mistakes.
- Provide a reproducible local workflow for official test packages when they are available.

Official PDFs and test packages are not committed. The repository keeps manifests and source links; the files are downloaded locally by the provided tools.

## Quick start

~~~bash
cp template.cpp cses/introductory/missing_number.cpp
make run FILE=cses/introductory/missing_number.cpp
~~~

For an SBC package:

~~~bash
make judge \
  FILE=solucoes/sbc/2025/primeira-fase/a.cpp \
  PACKAGE=simulados-sbc/2025/primeira-fase/downloads/packages_warmup.tar \
  PROBLEM=A
~~~

## Repository layout

| Path | Purpose |
|---|---|
| cses/ | CSES solutions grouped by problem-set section |
| solucoes/sbc/ | Solutions for SBC/ICPC practice contests |
| simulados-sbc/ | Local contest cache and download manifests |
| tools/fetch_sbc.py | Discovers and downloads official SBC materials |
| tools/judge_sbc.py | Runs a solution against an official SBC/ICPC package |
| include/ | Small, tested personal library |
| template.cpp | Portable C++ starting point |
| Makefile | Build, run, test, and judge commands |

Source files use lowercase snake_case. Contest solutions use the problem letter when appropriate, such as a.cpp or b.cpp.

## Local commands

~~~bash
make build FILE=path/to/solution.cpp
make run FILE=path/to/solution.cpp
make test FILE=solution.cpp INPUT=case.in EXPECTED=case.out
make judge FILE=solution.cpp PACKAGE=package.tar PROBLEM=A
~~~

The local environment uses Apple Clang 21.0.0 and C++20. The template uses standard C++ headers and does not depend on bits/stdc++.h.

## CSES workflow

1. Select a task from the [CSES Problem Set](https://cses.fi/problemset/).
2. Solve and test it locally.
3. Submit the source through the task page on CSES.
4. Keep accepted solutions under the corresponding cses/ section.

The CSES judge remains the source of truth because its tests are hidden. The local Makefile is for fast compilation and debugging.

## SBC workflow

1. Select an unused contest from the [SBC historical archive](https://maratona.sbc.org.br/hist/).
2. Run the contest under the intended time limit without opening test packages.
3. Store solutions under solucoes/sbc/<year>/<stage>/.
4. After the contest, run make judge when an official package exists.
5. Record the technique, complexity, result, and mistake in the solution or commit message.

## Recommended resources

- [CSES Problem Set](https://cses.fi/problemset/) - structured practice.
- [Competitive Programmer's Handbook](https://cses.fi/book/book.pdf) - concise theory reference.
- [USACO Guide](https://usaco.guide/) - topic-based explanations and problem lists.
- [cp-algorithms](https://cp-algorithms.com/) - algorithm reference and implementations.
- [AtCoder Educational DP Contest](https://atcoder.jp/contests/dp/tasks) - progressive dynamic programming practice.
- [Codeforces](https://codeforces.com/) - contests and problem volume.
- [SBC historical archive](https://maratona.sbc.org.br/hist/) - target contest material.

## GitHub

Recommended repository name: competitive-programming.

Suggested description:

> C++ competitive programming practice, CSES solutions, ICPC/SBC workflows, and local judging tools.

Recommended topics:

competitive-programming, cpp, algorithms, data-structures, cses, icpc, problem-solving.

The downloaded files and build artifacts are excluded by .gitignore. Only source code, manifests, documentation, and scripts should be committed.


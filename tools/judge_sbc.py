#!/usr/bin/env python3
"""Executa uma solução C++ contra um pacote oficial SBC/ICPC de um problema.

Não extrai arquivos do pacote: lê o ZIP interno diretamente em memória. Isso
evita problemas de segurança de extração e mantém o acervo intacto.
"""

from __future__ import annotations

import argparse
import io
import subprocess
import sys
import tarfile
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "build" / "judge"
CXX_FLAGS = [
    "-std=c++20", "-O2", "-pipe", "-Wall", "-Wextra", "-Wshadow",
    "-Wconversion", "-Wno-sign-conversion",
]


class PackageError(RuntimeError):
    pass


def zip_members_from_package(package: Path, problem: str) -> zipfile.ZipFile:
    """Return the requested problem ZIP without extracting an untrusted archive."""
    wanted = f"{problem.upper()}.ZIP"
    if tarfile.is_tarfile(package):
        with tarfile.open(package, "r:*") as archive:
            members = [member for member in archive.getmembers()
                       if member.isfile() and Path(member.name).name.upper() == wanted]
            if not members:
                available = sorted(Path(member.name).name for member in archive.getmembers()
                                   if member.isfile() and member.name.lower().endswith(".zip"))
                raise PackageError(f"Problema {problem} não encontrado. ZIPs disponíveis: {', '.join(available)}")
            stream = archive.extractfile(members[0])
            if stream is None:
                raise PackageError(f"Não foi possível ler {members[0].name}")
            return zipfile.ZipFile(io.BytesIO(stream.read()))
    if zipfile.is_zipfile(package):
        return zipfile.ZipFile(package)
    raise PackageError(f"Pacote não suportado: {package}")


def test_cases(problem_zip: zipfile.ZipFile) -> list[tuple[str, bytes, bytes]]:
    """Read pairs input/<case> and output/<case> used by ICPC problem packages."""
    names = set(problem_zip.namelist())
    inputs = [name for name in names if name.startswith("input/") and not name.endswith("/")]
    pairs: list[tuple[str, bytes, bytes]] = []
    for input_name in sorted(inputs):
        suffix = input_name[len("input/"):]
        output_name = f"output/{suffix}"
        if output_name in names:
            pairs.append((suffix, problem_zip.read(input_name), problem_zip.read(output_name)))
    if not pairs:
        raise PackageError("Layout sem pares input/<caso> e output/<caso>; este pacote precisa de adaptador.")
    return pairs


def compile_solution(source: Path) -> Path:
    BUILD.mkdir(parents=True, exist_ok=True)
    binary = BUILD / "solution"
    command = ["c++", *CXX_FLAGS, str(source), "-o", str(binary)]
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    if result.returncode:
        sys.stderr.buffer.write(result.stderr)
        raise PackageError("Falha de compilação.")
    return binary


def equal_output(actual: bytes, expected: bytes, strict: bool) -> bool:
    return actual == expected if strict else actual.split() == expected.split()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--file", required=True, type=Path, help="Solução C++.")
    parser.add_argument("--package", required=True, type=Path, help="Arquivo .tar ou .zip oficial.")
    parser.add_argument("--problem", required=True, help="Letra do problema, por exemplo A.")
    parser.add_argument("--timeout", type=float, default=4.0, help="Limite de parede por caso, em segundos.")
    parser.add_argument("--strict", action="store_true", help="Exige igualdade byte a byte; o padrão ignora espaços finais.")
    parser.add_argument("--max-cases", type=int, help="Executa somente os primeiros N casos (diagnóstico rápido).")
    args = parser.parse_args()

    if not args.file.is_file():
        parser.error(f"solução não encontrada: {args.file}")
    if not args.package.is_file():
        parser.error(f"pacote não encontrado: {args.package}")
    try:
        problem_zip = zip_members_from_package(args.package, args.problem)
        cases = test_cases(problem_zip)
        if args.max_cases is not None:
            cases = cases[:args.max_cases]
        binary = compile_solution(args.file)
    except PackageError as error:
        print(f"ERRO: {error}", file=sys.stderr)
        return 2

    totals = {"AC": 0, "WA": 0, "TLE": 0, "RE": 0}
    for name, input_data, expected in cases:
        try:
            result = subprocess.run([str(binary)], input=input_data, stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE, timeout=args.timeout, check=False)
        except subprocess.TimeoutExpired:
            totals["TLE"] += 1
            print(f"TLE  {name}")
            continue
        if result.returncode:
            totals["RE"] += 1
            print(f"RE   {name} (exit {result.returncode})")
        elif equal_output(result.stdout, expected, args.strict):
            totals["AC"] += 1
        else:
            totals["WA"] += 1
            print(f"WA   {name}")

    total = sum(totals.values())
    print(f"Resultado {args.problem.upper()}: {totals['AC']}/{total} AC | "
          f"WA {totals['WA']} | TLE {totals['TLE']} | RE {totals['RE']}")
    return 0 if totals["AC"] == total else 1


if __name__ == "__main__":
    raise SystemExit(main())

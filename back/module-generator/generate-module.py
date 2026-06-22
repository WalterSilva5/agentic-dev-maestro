import sys
import os
import pathlib
import argparse
import glob

ABSOLUTE_PATH=pathlib.Path(__file__).parent

class bcolors:
    FAIL = '\033[91m'

def generateModule():
  parser = argparse.ArgumentParser()
  parser.add_argument('--module', '-m', help="nome do modulo", type= str)

  if "-h" in sys.argv:
    print(parser.format_help())
    exit(0)

  args = parser.parse_args()

  if not args.module:
    print(parser.format_help())
    print("O nome do modulo é obrigatório")
    exit(1)

  MODULE=str(args.module)
  PATH=f"{ABSOLUTE_PATH.parent.resolve()}/src/modules/{MODULE}"

  if os.path.exists(PATH):
    print(f"{bcolors.FAIL} O modulo {MODULE} já existe {bcolors.ENDC}")
    exit(0)

  os.mkdir(PATH)
  print(f"✅ Pasta {MODULE} criada")

  MODULE_PASCALCASE=MODULE[0].upper() + MODULE[1:]

  files = glob.glob(f"{str(ABSOLUTE_PATH.resolve())}/*.txt")

  for file in files:
    with open(file, "r") as f:
      content = f.read()
      content = content.replace("module_lc", MODULE.lower())
      content = content.replace("Module_pc", MODULE_PASCALCASE)
      content = content.replace("MODULE", MODULE.upper())
      filename=file.split('/')[-1].replace('.txt', '.ts')
      result_filename=f"{MODULE.lower()}.{filename}"
      folder=""
      if "dto" in filename:
        folder="/dto"
        os.mkdir(PATH + folder)
      with open(f"{PATH}{folder}/{result_filename}", "x") as f:
        f.write(content)
        if folder:
          print(f"✅ Arquivo {folder[1:]}/{result_filename} criado")
        else:
          print(f"✅ Arquivo {result_filename} criado")

if __name__ == "__main__":
  generateModule()

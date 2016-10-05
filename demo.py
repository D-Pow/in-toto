import os
import sys
import subprocess

import toto.ssl_crypto.keys
import toto.models.layout as m
import toto.util
import toto.log as log


def wait_for_y(prompt):
  inp = False
  while inp != "":
    try:
      inp = raw_input("%s (enter)" % prompt)
      print inp
    except Exception, e:
      pass

def main():
  print """
  #############################################################################
  # Define the supply chain
  #############################################################################
  """

  # Get keys
  alice_key = toto.util.create_and_persist_or_load_key("alice")
  bob_key = toto.util.create_and_persist_or_load_key("bob")

  # Create Layout
  layout = m.Layout.read({ 
    "_type": "layout",
    "expires": "EXPIRES",
    "keys": {
        alice_key["keyid"]: alice_key,
        bob_key["keyid"]: bob_key
    },
    "steps": [{
        "name": "write-code",
        "material_matchrules": [],
        "product_matchrules": [["CREATE", "foo.py"]],
        "pubkeys": [alice_key["keyid"]],
        "expected_command": "vi",
      },
      {
        "name": "package",
        "material_matchrules": [
            ["MATCH", "PRODUCT", "foo.py", "FROM", "write-code"],
        ],
        "product_matchrules": [
            ["CREATE", "foo.tar.gz"],
        ],
        "pubkeys": [bob_key["keyid"]],
        "expected_command": "tar zcvf foo.tar.gz foo.py",
      }],
    "inspect": [{
        "name": "untar",
        "material_matchrules": [
            ["MATCH", "PRODUCT", "foo.tar.gz", "FROM", "package"]
        ],
        "product_matchrules": [
            ["MATCH", "PRODUCT", "foo.py", "FROM", "write-code"],
        ],
        "run": "tar xfz foo.tar.gz",
      }],
    "signatures": []
  })

  # Sign and dump layout
  layout.sign(alice_key)
  layout.dump()


  # Check if dumping - reading - dumping produces the same layout
  # layout_same = m.Layout.read_from_file("root.layout")
  # if repr(layout) != repr(layout_same):
  #   log.failing("There is something wrong with layout de-/serialization")


  wait_for_y("Wanna do the peachy supply chain?")

  print """
  #############################################################################
  # Do the peachy supply chain
  #############################################################################
  """


  write_code_cmd = "python -m toto.toto-run "\
                   "--name write-code --products foo.py "\
                   "--key alice -- vi foo.py"
  log.doing("(Alice) - %s" % write_code_cmd)

  wait_for_y("Wanna drop to vi and write peachy code?")
  subprocess.call(write_code_cmd.split())

  package_cmd = "python -m toto.toto-run "\
                "--name package --material foo.py --products foo.tar.gz "\
                "--key bob --record-byproducts -- tar zcvf foo.tar.gz foo.py"
  log.doing("(Bob) - %s" % package_cmd)
  subprocess.call(package_cmd.split())


  print """
  #############################################################################
  # Verify the peachy supply chain
  #############################################################################
  """

  verify_cmd = "python -m toto.toto-verify "\
               "--layout root.layout "\
               "--layout-key alice"
  log.doing("(User) - %s" % verify_cmd)
  subprocess.call(verify_cmd.split())

  wait_for_y("Wanna do the failing supply chain?")

  print """
  #############################################################################
  # Do the failing supply chain
  #############################################################################
  """

  write_code_cmd = "python -m toto.toto-run "\
                   "--name write-code --products foo.py "\
                   "--key alice -- vi foo.py"
  log.doing("(Alice) - %s" % write_code_cmd)
  wait_for_y("Wanna drop to vi and write peachy code?")
  subprocess.call(write_code_cmd.split())


  bad_cmd = "vi foo.py"
  wait_for_y("Wanna drop to vi and write baaad code?")
  log.doing("(Malory) - %s" % bad_cmd)

  subprocess.call(bad_cmd.split())


  package_cmd = "python -m toto.toto-run "\
                "--name package --material foo.py --products foo.tar.gz "\
                "--key bob --record-byproducts -- tar zcvf foo.tar.gz foo.py"
  log.doing("(Bob) - %s" % package_cmd)
  subprocess.call(package_cmd.split())



  print """
  #############################################################################
  # Verify the failing supply chain
  #############################################################################
  """

  verify_cmd = "python -m toto.toto-verify "\
               "--layout root.layout "\
               "--layout-key alice"
  log.doing("(User) - %s" % verify_cmd)
  subprocess.call(verify_cmd.split())


if __name__ == '__main__':
  main()

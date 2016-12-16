#!/usr/bin/env python

"""
<Program Name>
  test_verifylib.py

<Author>
  Lukas Puehringer <lukas.puehringer@nyu.edu>

<Started>
  Nov 07, 2016

<Copyright>
  See LICENSE for licensing information.

<Purpose>
  Test verifylib functions.

"""

import unittest
from in_toto.models.link import Link
from in_toto.models.layout import Step, Inspection
from in_toto.verifylib import verify_delete_rule, verify_create_rule, \
    verify_match_rule, verify_item_rules, verify_all_item_rules, \
    verify_command_alignment
from in_toto.exceptions import RuleVerficationFailed
from mock import patch

class TestVerifyCommandAlignment(unittest.TestCase):
  """Test verifylib.verify_command_alignment(command, expected_command)"""

  def setUp(self):
    self.command = ["vi", "file1", "file2"]

  def test_commands_align(self):
    """Cmd and expected cmd are equal, passes. """
    expected_command = ["vi", "file1", "file2"]
    verify_command_alignment(self.command, expected_command)

  def test_commands_do_not_fully_align_log_warning(self):
    """Cmd and expected cmd differ slightly. """
    expected_command = ["/usr/bin/vi", "file1", "file2"]

    with patch("in_toto.verifylib.log") as mock_logging:
      verify_command_alignment(self.command, expected_command)
      mock_logging.warning.assert_called_with("Run command '{0}'"
          " differs from expected command '{1}'"
          .format(self.command, expected_command))

  def test_commands_do_not_align_at_all_log_warning(self):
    """Cmd and expected cmd differ completely. """
    expected_command = ["make install"]

    with patch("in_toto.verifylib.log") as mock_logging:
      verify_command_alignment(self.command, expected_command)
      mock_logging.warning.assert_called_with("Run command '{0}'"
          " differs from expected command '{1}'"
          .format(self.command, expected_command))


class TestVerifyDeleteRule(unittest.TestCase):
  """Test verifylib.verify_delete_rule(rule, artifact_queue) """

  def setUp(self):
    """ Setup artifact queues. """
    self.artifact_queue = ["foo"]
    self.artifact_queue_empty = []


  def test_fail_delete_file(self):
    """["DELETE", "foo"], matches foo (not deleted), fails. """

    rule = ["DELETE", "foo"]
    with self.assertRaises(RuleVerficationFailed):
      verify_delete_rule(rule, self.artifact_queue)


  def test_fail_delete_star(self):
    """["DELETE", "*"], matches * in non-empty queue (not deleted), fails. """

    rule = ["DELETE", "*"]
    with self.assertRaises(RuleVerficationFailed):
        verify_delete_rule(rule, self.artifact_queue)


  def test_pass_delete_file(self):
    """["DELETE", "bar"] does not match bar (deleted), passes. """

    rule = ["DELETE", "bar"]
    self.assertIsNone(
        verify_delete_rule(rule, self.artifact_queue))


  def test_pass_delete_star(self):
    """["DELETE", "*"], does not match * in empty queue (deleted), passes. """

    rule = ["DELETE", "*"]
    self.assertIsNone(
        verify_delete_rule(rule, self.artifact_queue_empty))


  def test_pass_ignore_case_keyword(self):
    """["delete", "bar"], ["DELETE", "bar"], ignores keyword case, passes. """

    rule1 = ["delete", "bar"]
    rule2 = ["DELETE", "bar"]
    self.assertIsNone(
        verify_delete_rule(rule1, self.artifact_queue))
    self.assertIsNone(
        verify_delete_rule(rule2, self.artifact_queue))





class TestVerifyCreateRule(unittest.TestCase):
  """Test verifylib.verify_create_rule(rule, artifact_queue) """

  def setUp(self):
    """ Setup artifact queues. """
    self.artifact_queue = ["foo"]
    self.artifact_queue_foostar = ["foo", "bar", "foobar"]
    self.artifact_queue_empty = []

  def test_fail_create_file(self):
    """["CREATE", "bar"], does not mach bar (not created), fails. """

    rule = ["CREATE", "bar"]
    with self.assertRaises(RuleVerficationFailed):
      verify_create_rule(rule, self.artifact_queue)


  def test_fail_create_star(self):
    """["CREATE", "*"], does not match * (nothing created), fails. """

    rule = ["CREATE", "*"]
    with self.assertRaises(RuleVerficationFailed):
        verify_create_rule(rule, self.artifact_queue_empty)


  def test_pass_create_file(self):
    """["CREATE", "foo"], matches foo (created), passes. """

    rule = ["CREATE", "foo"]
    self.assertListEqual(
      verify_create_rule(rule, self.artifact_queue), [])


  def test_pass_create_star(self):
    """["CREATE", "*"], matches * in non-empty queue (created), passes. """

    rule = ["CREATE", "*"]
    self.assertListEqual(
        verify_create_rule(rule, self.artifact_queue), [])


  def test_remove_foostar_from_artifact_queue(self):
    """["CREATE", "foo*"], matches foo* (created), passes. """

    rule = ["CREATE", "foo*"]
    self.assertListEqual(
        verify_create_rule(rule, self.artifact_queue_foostar), ["bar"])


  def test_pass_ignore_case_keyword(self):
    """["create", "bar"], ["CREATE", "bar"], ignores keyword case, passes. """

    rule1 = ["create", "foo"]
    rule2 = ["CREATE", "foo"]
    self.assertListEqual(
        verify_create_rule(rule1, self.artifact_queue), [])
    self.assertListEqual(
        verify_create_rule(rule2, self.artifact_queue), [])





class TestVerifyMatchRule(unittest.TestCase):
  """Test verifylib.verify_match_rule(rule, artifact_queue, artifacts, links) """

  def setUp(self):
    """Setup artifact queues, artifacts dictionary and Link dictionary. """

    # Dummy artifact hashes
    self.sha256_foo = \
        "d65165279105ca6773180500688df4bdc69a2c7b771752f0a46ef120b7fd8ec3"
    self.sha256_foobar = \
        "155c693a6b7481f48626ebfc545f05236df679f0099225d6d0bc472e6dd21155"
    self.sha256_bar = \
        "cfdaaf1ab2e4661952a9dec5e8fa3c360c1b06b1a073e8493a7c46d2af8c504b"
    self.sha256_barfoo = \
        "2036784917e49b7685c7c17e03ddcae4a063979aa296ee5090b5bb8f8aeafc5d"

    # Link dictionary containing dummy artifacts related to Steps the rule is
    # matched with (match target).
    materials = {
      "foo": {"sha256": self.sha256_foo},
      "foobar": {"sha256": self.sha256_foobar}
    }
    products = {
      "bar": {"sha256": self.sha256_bar},
      "barfoo": {"sha256": self.sha256_barfoo}
      }

    # Note: For simplicity the Links don't have all usually required fields set
    self.links = {
        "link-1" : Link(name="link-1", materials=materials, products=products),
    }


  def test_pass_match_material(self):
    """["MATCH", "MATERIAL", "foo", "FROM", "link-1"],
    source artifact foo and target material foo hashes match, passes. """

    rule = ["MATCH", "MATERIAL", "foo", "FROM", "link-1"]
    artifacts = {
      "foo": {"sha256": self.sha256_foo}
    }
    queue = artifacts.keys()
    self.assertListEqual(
        verify_match_rule(rule, queue, artifacts, self.links), [])


  def test_pass_match_product(self):
    """["MATCH", "PRODUCT", "bar", "FROM", "link-1"],
    source artifact bar and target product bar hashes match, passes. """

    rule = ["MATCH", "PRODUCT", "bar", "FROM", "link-1"]
    artifacts = {
      "bar": {"sha256": self.sha256_bar}
    }
    queue = artifacts.keys()
    self.assertListEqual(
        verify_match_rule(rule, queue, artifacts, self.links), [])


  def test_pass_match_material_star(self):
    """["MATCH", "MATERIAL", "foo*", "FROM", "link-1"],
    source artifacts foo* match target materials foo* hashes, passes. """

    rule = ["MATCH", "MATERIAL", "foo*", "FROM", "link-1"]
    artifacts = {
      "foo": {"sha256": self.sha256_foo},
      "foobar": {"sha256": self.sha256_foobar}
    }
    queue = artifacts.keys()
    self.assertListEqual(
        verify_match_rule(rule, queue, artifacts, self.links), [])


  def test_pass_match_product_star(self):
    """["MATCH", "PRODUCT", "bar*", "FROM", "link-1"],
    source artifacts bar* match target products bar* hashes, passes. """

    rule = ["MATCH", "PRODUCT", "bar*", "FROM", "link-1"]
    artifacts = {
      "bar": {"sha256": self.sha256_bar},
      "barfoo": {"sha256": self.sha256_barfoo}
    }
    queue = artifacts.keys()
    self.assertListEqual(
        verify_match_rule(rule, queue, artifacts, self.links), [])


  def test_fail_more_artifacts_in_target_than_in_source(self):
    """["MATCH", "PRODUCT", "bar*", "FROM", "link-1"],
    pattern found to artifacts in target, only one in source, fails."""
    rule = ["MATCH", "PRODUCT", "bar*", "FROM", "link-1"]
    artifacts = {
      "bar": {"sha256": self.sha256_bar},
    }
    queue = artifacts.keys()
    with self.assertRaises(RuleVerficationFailed):
      verify_match_rule(rule, queue, artifacts, self.links)


  def test_fail_artifact_found_in_source_not_in_target(self):
    """["MATCH", "MATERIAL", "bar", "FROM", "link-1"],
    pattern found in source but not in target, fails. """
    rule = ["MATCH", "MATERIAL", "bar", "FROM", "link-1"]

    artifacts = {
      "bar": {"sha256": self.sha256_bar},
    }
    queue = artifacts.keys()
    with self.assertRaises(RuleVerficationFailed):
      verify_match_rule(rule, queue, artifacts, self.links)


  def test_fail_artifact_found_in_target_not_in_source(self):
    """["MATCH", "MATERIAL", "foo", "FROM", "link-1"],
    pattern found in target but not in source, fails. """
    rule = ["MATCH", "MATERIAL", "foo", "FROM", "link-1"]

    artifacts = {
      "bar": {"sha256": self.sha256_bar},
    }
    queue = artifacts.keys()
    with self.assertRaises(RuleVerficationFailed):
      verify_match_rule(rule, queue, artifacts, self.links)


  def test_fail_artifact_found_in_target_not_in_source_queue(self):
    """["MATCH", "MATERIAL", "foo", "FROM", "link-1"],
    pattern found in target and source but not in source queue, fails. """
    rule = ["MATCH", "MATERIAL", "foo", "FROM", "link-1"]

    artifacts = {
      "foo": {"sha256": self.sha256_foo},
    }
    queue = ["bar"]
    with self.assertRaises(RuleVerficationFailed):
      verify_match_rule(rule, queue, artifacts, self.links)


  def test_fail_hashes_do_not_match(self):
    """["MATCH", "MATERIAL", "foo", "FROM", "link-1"],
    pattern found but hashes do not match, fails. """

    rule = ["MATCH", "MATERIAL", "foo", "FROM", "link-1"]
    artifacts = {
      "foo": {"sha256": self.sha256_bar},
    }
    queue = artifacts.keys()
    with self.assertRaises(RuleVerficationFailed):
      verify_match_rule(rule, queue, artifacts, self.links)





class TestVerifyItemRules(unittest.TestCase):
  """Test verifylib.verify_item_rules(item_name, rules, artifacts, links)"""

  def setUp(self):
    self.item_name = "test-item"
    self.sha256_foo = \
        "d65165279105ca6773180500688df4bdc69a2c7b771752f0a46ef120b7fd8ec3"
    self.sha256_bar = \
        "cfdaaf1ab2e4661952a9dec5e8fa3c360c1b06b1a073e8493a7c46d2af8c504b"

    self.artifacts = {
      "foo": {"sha256": self.sha256_foo},
      "bar": {"sha256": self.sha256_bar}
    }
    self.links = {
      "link-1": Link(name="link-1",
          materials={}, products={"foo": {"sha256": self.sha256_foo}})
    }


  def test_pass_with_rule_of_each_type(self):
    """Pass with list of rules of each rule type. """

    rules = [
      ["CREATE", "bar"],
      ["DELETE", "baz"],
      ["MATCH", "PRODUCT", "foo", "FROM", "link-1"]
    ]
    verify_item_rules(self.item_name, rules, self.artifacts, self.links)


  def test_fail_with_conflicting_rules(self):
    """Fail with artifact being matched by a match and by a create rule."""

    rules = [
      ["MATCH", "PRODUCT", "foo", "FROM", "link-1"],
      ["CREATE", "foo"]
    ]
    with self.assertRaises(RuleVerficationFailed):
      verify_item_rules(self.item_name, rules, self.artifacts, self.links)

    rules = [
      ["CREATE", "foo"],
      ["MATCH", "PRODUCT", "foo", "FROM", "link-1"]
    ]
    with self.assertRaises(RuleVerficationFailed):
      verify_item_rules(self.item_name, rules, self.artifacts, self.links)

  def test_fail_unmatched_artifacts(self):
    """Fail with unmatched artifacts after executing all rules. """

    rules = []
    with self.assertRaises(RuleVerficationFailed):
      verify_item_rules(self.item_name, rules, self.artifacts, {})





class TestVerifyAllItemRules(unittest.TestCase):
  """Test verifylib.verify_all_item_rules(items, links, target_links=None). """

  def setUp(self):
    """Create a dummy supply chain with two steps one inspection and the
    according link metadata:

    write-code (Step) ->  package (step) -> untar (Inspection)

    'write-code' creates an artifact foo
    'package' creates foo.tar.gz and deletes foo
    'untar' untars foo.tar.gz which results in foo.tar.gz and foo

    """

    self.sha256_foo = \
        "d65165279105ca6773180500688df4bdc69a2c7b771752f0a46ef120b7fd8ec3"
    self.sha256_foo_tar = \
        "93c3c35a039a6a3d53e81c5dbee4ebb684de57b7c8be11b8739fd35804a0e918"

    self.steps = [
        Step(name="write-code",
            product_matchrules=[
                ["CREATE", "foo"]
            ],
        ),
        Step(name="package",
            material_matchrules=[
                ["MATCH", "PRODUCT", "foo", "FROM", "write-code"]
            ],
            product_matchrules=[
                ["CREATE", "foo.tar.gz"],
                ["DELETE", "foo"]
            ],
        )
    ]

    self.inspections = [
        Inspection(name="untar",
            material_matchrules=[
                ["MATCH", "PRODUCT", "foo.tar.gz", "FROM", "package"]
            ],
            product_matchrules=[
                ["MATCH", "PRODUCT", "foo", "FROM", "write-code"]
            ]
        )
    ]

    self.step_links = {
      "write-code" : Link(name="write-code",
          products={
              "foo": {
                  "sha256": self.sha256_foo
              }
          }
      ),
      "package" : Link(name="package",
          materials={
              "foo": {
                  "sha256": self.sha256_foo
              }
          },
          products={
              "foo.tar.gz": {
                  "sha256": self.sha256_foo_tar
              }
          }
      )
    }

    self.inspection_links = {
        "untar" : Link(name="untar",
            materials={
                "foo.tar.gz": {
                    "sha256": self.sha256_foo_tar
                }
            },
            products={
                "foo": {
                    "sha256": self.sha256_foo
                },
            }
        )
    }

  def test_pass_verify_all_step_rules(self):
    """Pass rule verification for dummy supply chain Steps. """
    verify_all_item_rules(self.steps, self.step_links)


  def test_pass_verify_all_inspection_rules(self):
    """Pass rule verification for dummy supply chain Inspections. """
    verify_all_item_rules(self.inspections, self.inspection_links,
        self.step_links)

if __name__ == '__main__':

  unittest.main()

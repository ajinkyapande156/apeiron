"""
Copyright (c) 2022 Nutanix Inc. All rights reserved.

Author: pritam.chatterjee@nutanix.com
"""
# pylint: disable=import-error, unused-import
try:
  from framework.lib.nulog import INFO, WARN, DEBUG, \
    ERROR  # pylint: disable=unused-import

  EXECUTOR = "nutest"
except Exception:  # pylint: disable=broad-except
  from libs.ahv.framework.proxy_logging \
    import INFO, WARN, DEBUG, ERROR  # pylint: disable=unused-import

  EXECUTOR = "mjolnir"


# NOTE: Move to base
class AbstractPrioritizer(object):
  """AbstractPrioritizer class"""

  def prioritize(self, **kwargs):
    """
    Method to perform prioritization
    Raises:
    """
    raise NotImplementedError


class DefaultPrioritizer(AbstractPrioritizer):
  """DefaultPrioritizer class"""

  def prioritize(self, **kwargs):
    """
    Method to perform prioritization
    Returns:
      test_plan(dict):
    Raises:
    """
    test_plan = kwargs.get("test_plan")
    temp_plan = sorted(test_plan, key=lambda x: x["tier"])
    groups = self._get_tier_groups(temp_plan)
    priority_plan = list()
    last_idx = -1
    for idx in groups:
      priority_plan += sorted(temp_plan[last_idx + 1:idx + 1],
                              key=lambda x: x["os"],
                              reverse=True)
      last_idx = idx
    priority_plan += sorted(temp_plan[last_idx + 1:],
                            key=lambda x: x["os"],
                            reverse=True)
    return priority_plan

  def _get_tier_groups(self, new_test_plan):
    """
    Internal method for getting tierwise partitiions
    Args:
      new_test_plan(list):
    Returns:
      groups(list):
    """
    DEBUG(self)
    groups = list()

    for i, entry in enumerate(new_test_plan[:-1]):
      if not entry["tier"] == new_test_plan[i + 1]["tier"]:
        groups.append(i)

    # for last entry
    if groups and groups[-1] == len(new_test_plan) - 1:
      groups.append(new_test_plan[-1])
    return groups

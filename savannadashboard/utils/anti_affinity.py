# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright (c) 2013 Mirantis Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from django.utils.translation import ugettext as _

from horizon import forms

from savannadashboard.api import client as savannaclient
import savannadashboard.utils.workflow_helpers as whelpers


def anti_affinity_field():
    return forms.MultipleChoiceField(
        label=_("Use anti-affinity groups for: "),
        required=False,
        help_text=_("Use anti-affinity groups for processes"),
        widget=forms.CheckboxSelectMultiple()
    )


def populate_anti_affinity_choices(self, request, context):
    savanna = savannaclient.Client(request)
    plugin, version = whelpers.get_plugin_and_hadoop_version(request)

    version_details = savanna.plugins.get_version_details(plugin, version)
    process_choices = []
    for service, processes in version_details.node_processes.items():
        for process in processes:
            process_choices.append((process, process))

    return process_choices
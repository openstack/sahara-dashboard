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

import json

from django.utils.translation import gettext_lazy as _

from horizon import exceptions

from sahara_dashboard.api import sahara as saharaclient
import sahara_dashboard.content.data_processing.clusters. \
    cluster_templates.workflows.create as create_flow
import sahara_dashboard.content.data_processing.utils. \
    workflow_helpers as wf_helpers
from sahara_dashboard import utils


class CopyClusterTemplate(create_flow.ConfigureClusterTemplate):
    success_message = _("Cluster Template copy %s created")
    entry_point = "generalconfigaction"

    def __init__(self, request, context_seed, entry_point, *args, **kwargs):
        self.cluster_template_id = context_seed["template_id"]
        try:
            self.template = saharaclient.cluster_template_get(
                request,
                self.cluster_template_id)
            self._set_configs_to_copy(self.template.cluster_configs)

            if saharaclient.VERSIONS.active == '2':
                version_attr = 'plugin_version'
            else:
                version_attr = 'hadoop_version'
            hadoop_version = getattr(self.template, version_attr)

            request.GET = request.GET.copy()
            request.GET.update({"plugin_name": self.template.plugin_name,
                                version_attr: hadoop_version,
                                "aa_groups": self.template.anti_affinity})

            super(CopyClusterTemplate, self).__init__(request, context_seed,
                                                      entry_point, *args,
                                                      **kwargs)
            # Initialize node groups.
            # TODO(rdopieralski) The same (or very similar) code appears
            # multiple times in this dashboard. It should be refactored to
            # a function.
            for step in self.steps:
                if isinstance(step, create_flow.ConfigureNodegroups):
                    ng_action = step.action
                    template_ngs = self.template.node_groups

                    if 'forms_ids' in request.POST:
                        continue
                    ng_action.groups = []
                    for i, templ_ng in enumerate(template_ngs):
                        group_name = "group_name_%d" % i
                        template_id = "template_id_%d" % i
                        count = "count_%d" % i
                        serialized = "serialized_%d" % i

                        # save the original node group with all its fields in
                        # case the template id is missing
                        serialized_val = utils.serialize(
                            json.dumps(wf_helpers.clean_node_group(templ_ng)))

                        ng = {
                            "name": templ_ng["name"],
                            "count": templ_ng["count"],
                            "id": i,
                            "deletable": "true",
                            "serialized": serialized_val
                        }
                        if "node_group_template_id" in templ_ng:
                            ng["template_id"] = templ_ng[
                                "node_group_template_id"]
                        ng_action.groups.append(ng)

                        wf_helpers.build_node_group_fields(
                            ng_action, group_name, template_id, count,
                            serialized)

                elif isinstance(step, create_flow.GeneralConfig):
                    fields = step.action.fields
                    fields["cluster_template_name"].initial = (
                        self.template.name + "-copy")
                    fields['use_autoconfig'].initial = (
                        self.template.use_autoconfig)
                    fields["description"].initial = self.template.description

                elif isinstance(step, create_flow.SelectClusterShares):
                    fields = step.action.fields
                    fields["shares"].initial = (
                        self._get_share_defaults(fields["shares"].choices)
                    )
                    fields['is_public'].initial = (
                        self.template.is_public)
                    fields['is_protected'].initial = (
                        self.template.is_protected)

                elif isinstance(step, create_flow.SelectDnsDomains):
                    fields = step.action.fields
                    fields["domain_name"].initial = self.template.domain_name

        except Exception:
            exceptions.handle(request,
                              _("Unable to fetch template to copy."))

    def _get_share_defaults(self, choices):
        values = dict()
        for i, choice in enumerate(choices):
            share_id = choice[0]
            s = [s for s in self.template.shares if s['id'] == share_id]
            if len(s) > 0:
                path = s[0]["path"] if "path" in s[0] else ""
                values["share_id_{0}".format(i)] = {
                    "id": s[0]["id"],
                    "path": path,
                    "access_level": s[0]["access_level"]
                }
            else:
                values["share_id_{0}".format(i)] = {
                    "id": None,
                    "path": None,
                    "access_level": None
                }
        return values

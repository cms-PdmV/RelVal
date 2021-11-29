<template>
  <div style="height: calc(100vh - 118px); overflow: auto;">
    <div style="display: flex;">
      <div style="flex: 1 1 auto;">
        <div>
          <div style="width: calc(100vw - 32px); position: sticky; left: 16px;">
            <h1 class="page-title">RelVals</h1>
            <ColumnSelector :columns="columns"
                            v-on:updateColumns="updateTableColumns"/>
          </div>
        </div>
        <v-data-table :headers="headers"
                      :items="dataItems"
                      :items-per-page="itemsPerPage"
                      :loading="loading"
                      :options.sync="optionsSync"
                      :server-items-length="totalItems"
                      hide-default-footer
                      class="elevation-1"
                      show-select
                      item-key="prepid"
                      v-model="selectedItems"
                      dense>
          <template v-slot:item._actions="{ item }">
            <div class="actions">
              <a :href="'relvals/edit?prepid=' + item.prepid" v-if="role('manager')">Edit</a>
              <a @click="deleteRelVals([item])" v-if="item.status == 'new' && role('manager')">Delete</a>
              <a :href="'relvals/edit?clone=' + item.prepid" v-if="role('manager')" title="Clone RelVal">Clone</a>
              <a :href="'api/relvals/get_cmsdriver/' + item.prepid" title="Show cmsDriver.py command for this RelVal">cmsDriver</a>
              <a :href="'api/relvals/get_dict/' + item.prepid" title="Show JSON dictionary for ReqMgr2">Job dict</a>
              <a @click="previousStatus([item])" v-if="role('manager') && item.status != 'new'" title="Move to previous status">Previous</a>
              <a @click="nextStatus([item])" v-if="role('manager') && item.status != 'done'" title="Move to next status">Next</a>
              <a @click="updateWorkflows([item])" v-if="role('administrator') && item.status == 'submitted' && !isDev" title="Update RelVal information from Stats2">Update from Stats2</a>
              <a target="_blank" :href="'https://cms-pdmv.cern.ch/stats?prepid=' + item.prepid" v-if="(item.status == 'submitted' || item.status == 'done' || item.status == 'archived') && !isDev" title="Show workflows of this RelVal in Stats2">Stats2</a>
              <a :href="'tickets?created_relvals=' + item.prepid" title="Show ticket that was used to create this RelVal">Ticket</a>
            </div>
          </template>
          <template v-slot:item.prepid="{ item }">
            <a :href="'relvals?prepid=' + item.prepid" title="Show only this RelVal">{{item.prepid}}</a>
          </template>
          <template v-slot:item.history="{ item }">
            <HistoryCell :data="item.history"/>
          </template>
          <template v-slot:item.notes="{ item }">
            <pre v-if="item.notes.length" v-html="sanitize(item.notes)" class="notes" v-linkified></pre>
          </template>
          <template v-slot:item.fragment="{ item }">
            <pre v-if="item.fragment.length" class="fragment">{{item.fragment}}</pre>
          </template>
          <template v-slot:item.memory="{ item }">
            {{item.memory}} MB
          </template>
          <template v-slot:item.steps="{ item }">
            <StepsCell :data="item.steps"/>
          </template>
          <template v-slot:item._workflow="{ item }">
            <a :href="'relvals?workflow_id=' + item.workflow_id">{{item.workflow_id}}</a> <span v-if="item.workflow_name">({{item.workflow_name}})</span>
          </template>
          <template v-slot:item.workflows="{ item }">
            <ol>
              <li v-for="(workflow, index) in item.workflows" :key="workflow.name">
                <a v-if="!isDev" target="_blank" title="Open workflow in ReqMgr2" :href="'https://cmsweb.cern.ch/reqmgr2/fetch?rid=' + workflow.name">{{workflow.name}}</a>&nbsp;
                <a v-if="isDev" target="_blank" title="Open workflow in ReqMgr2" :href="'https://cmsweb-testbed.cern.ch/reqmgr2/fetch?rid=' + workflow.name">{{workflow.name}}</a>&nbsp;
                <template v-if="!isDev">
                  <small> open in:</small> <a target="_blank" title="Open workflow in Stats2" :href="'https://cms-pdmv.cern.ch/stats?workflow_name=' + workflow.name">Stats2</a>&nbsp;
                </template>
                <template v-if="workflow.status_history && workflow.status_history.length > 0">
                  <small> status:</small> {{workflow.status_history[workflow.status_history.length - 1].status}}
                </template>
                <ul v-if="index == item.workflows.length - 1" class="zebra-datasets">
                  <li v-for="dataset in workflow.output_datasets" :key="dataset.name">
                    <div>
                      <div class="gray-bar">
                        <div :style="'width: ' +  dataset.completed + '%;'" :class="'bar ' + dataset.type.toLowerCase() + '-bar'"></div>
                      </div>
                      <small>datatier:</small> {{dataset.datatier}},
                      <small>completed:</small> {{dataset.completed}}%,
                      <small>events:</small> {{dataset.niceEvents}},
                      <small>type:</small> <b :class="dataset.type.toLowerCase() + '-type'">{{dataset.type}}</b>
                      <br>
                      <small style="letter-spacing: -0.1px"><a target="_blank" title="Open dataset in DAS" :href="makeDASLink(dataset.name)">{{dataset.name}}</a></small>
                    </div>
                  </li>
                </ul>
              </li>
            </ol>
          </template>
          <template v-slot:item.output_datasets="{ item }">
            <ul>
              <li v-for="dataset in item.output_datasets" :key="dataset"><a target="_blank" title="Open dataset in DAS" :href="makeDASLink(dataset)">{{dataset}}</a></li>
            </ul>
          </template>
          <template v-slot:item.time_per_event="{ item }">
            {{item.time_per_event}}s
          </template>
          <template v-slot:item.size_per_event="{ item }">
            {{item.size_per_event}} kB
          </template>
          <template v-slot:item.recycle_gs="{ item }">
            {{item.recycle_gs ? 'Yes' : 'No'}}
          </template>
          <template v-slot:item.cmssw_release="{ item }">
            <a :href="'relvals?cmssw_release=' + item.cmssw_release" :title="'Show all RelVals with ' + item.cmssw_release + ' CMSSW release'">{{item.cmssw_release}}</a>
            <template v-if="item.scram_arch">
              <br>
              <small><a :href="'relvals?scram_arch=' + item.scram_arch" :title="'Show all RelVals with ' + item.scram_arch + ' SCRAM arch'">{{item.scram_arch}}</a></small>
            </template>
          </template>
          <template v-slot:item.batch_name="{ item }">
            <a :href="'relvals?batch_name=' + item.batch_name" :title="'Show all RelVals with ' + item.batch_name + ' batch name'">{{item.batch_name}}</a>
          </template>
          <template v-slot:item.campaign_timestamp="{ item }">
            <template v-if="item.campaign_timestamp">
              <a :href="'relvals?cmssw_release=' + item.cmssw_release + '&batch_name=' + item.batch_name + '&campaign_timestamp=' + item.campaign_timestamp" :title="'Show RelVals in ' + item.cmssw_release + '__' + item.batch_name + ' campaign with ' + item.campaign_timestamp + ' timestamp'">{{item.cmssw_release + '__' + item.batch_name + '-' + item.campaign_timestamp}}</a>
              <small> ({{niceDate(item.campaign_timestamp)}})</small>
            </template>
            <template v-else>
              Not set
            </template>
          </template>
          <template v-slot:item.status="{ item }">
            <a :href="'relvals?status=' + item.status" :title="'Show all RelVals with status ' + item.status">{{item.status}}</a>
          </template>
          <template v-slot:item.matrix="{ item }">
            <a :href="'relvals?matrix=' + item.matrix" :title="'Show all RelVals with ' + item.matrix + ' matrix'">{{item.matrix}}</a>
          </template>
          <template v-slot:item.sample_tag="{ item }">
            <a :href="'relvals?sample_tag=' + item.sample_tag" :title="'Show all RelVals with ' + item.sample_tag + ' sample tag'">{{item.sample_tag}}</a>
          </template>
          <template v-slot:item.label="{ item }">
            <a :href="'relvals?label=' + item.label" :title="'Show all RelVals with ' + item.label + ' label'">{{item.label}}</a>
          </template>
          <template v-slot:item._gpu="{ item }">
            <ul style="padding-left: 0; list-style: none;">
              <li v-for="(step, index) in item.steps" :key="index">
                <template v-if="stepSteps(step)">
                  {{stepSteps(step)}}: {{step.gpu.requires}}
                  <ul v-if="step.gpu.requires != 'forbidden'">
                    <li v-if="step.gpu.gpu_memory">GPUMemory: {{step.gpu.gpu_memory}} MB</li>
                    <li v-if="step.gpu.cuda_capabilities.length">CUDACapabilities: {{step.gpu.cuda_capabilities.join(',')}}</li>
                    <li v-if="step.gpu.cuda_runtime">CUDARuntime: {{step.gpu.cuda_runtime}}</li>
                    <li v-if="step.gpu.gpu_name">GPUName: {{step.gpu.gpu_name}}</li>
                    <li v-if="step.gpu.cuda_driver_version">CUDADriverVersion: {{step.gpu.cuda_driver_version}}</li>
                    <li v-if="step.gpu.cuda_runtime_version">CUDARuntimeVersion: {{step.gpu.cuda_runtime_version}}</li>
                  </ul>
                </template>
              </li>
            </ul>
          </template>
        </v-data-table>
      </div>
    </div>

    <v-dialog v-model="dialog.visible"
              max-width="50%">
      <v-card>
        <v-card-title class="headline">
          {{dialog.title}}
        </v-card-title>
        <v-card-text>
          <span v-html="dialog.description"></span>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn small class="mr-1 mb-1" color="primary" v-if="dialog.cancel" @click="dialog.cancel">
            Cancel
          </v-btn>
          <v-btn small class="mr-1 mb-1" color="error" @click="dialog.ok">
            OK
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <v-dialog v-model="errorDialog.visible"
              max-width="50%">
      <v-card>
        <v-card-title class="headline">
          {{errorDialog.title}}
        </v-card-title>
        <v-card-text>
          <span v-html="errorDialog.description"></span>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn small class="mr-1 mb-1" color="primary" @click="errorDialog.visible = false">
            Dismiss
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <footer>
      <div class="actions" style="float: left; line-height: 52px">
        <a :href="'relvals/edit'" v-if="role('manager') && !selectedItems.length">New RelVal</a>
        <span v-if="role('manager') && selectedItems.length">Selected items ({{selectedItems.length}}) actions:</span>
        <a v-if="role('manager') && selectedItems.length" @click="editRelVals(selectedItems)" title="Edit selected RelVals">Edit</a>
        <a v-if="role('manager') && selectedItems.length" @click="deleteRelVals(selectedItems)" title="Delete selected RelVals">Delete</a>
        <a v-if="role('manager') && selectedItems.length" @click="previousStatus(selectedItems)" title="Move selected RelVals to previous status">Previous</a>
        <a v-if="role('manager') && selectedItems.length" @click="nextStatus(selectedItems)" title="Move selected RelVals to next status">Next</a>
        <a v-if="role('administrator') && selectedItems.length" @click="updateWorkflows(selectedItems)" title="Update selected RelVals' information from Stats2">Update from Stats2</a>
        <a v-if="selectedItems.length" @click="openPmpMany(selectedItems)" title="Show selected RelVals in pMp">pMp</a>
      </div>
      <Paginator :totalRows="totalItems"
                 v-on:update="onPaginatorUpdate"/>
    </footer>
  </div>
</template>

<script>
import axios from 'axios'
import ColumnSelector from './ColumnSelector'
import Paginator from './Paginator'
import HistoryCell from './HistoryCell'
import StepsCell from './StepsCell'
import { roleMixin } from '../mixins/UserRoleMixin.js'
import { utilsMixin } from '../mixins/UtilsMixin.js'
import dateFormat from 'dateformat'

export default {
  components: {
    ColumnSelector,
    Paginator,
    HistoryCell,
    StepsCell
  },
  mixins: [roleMixin, utilsMixin],
  data () {
    return {
      databaseName: undefined,
      columns: [
        {'dbName': 'prepid', 'displayName': 'PrepID', 'visible': 1, 'sortable': true},
        {'dbName': '_actions', 'displayName': 'Actions', 'visible': 1},
        {'dbName': 'status', 'displayName': 'Status', 'visible': 1, 'sortable': true},
        {'dbName': 'batch_name', 'displayName': 'Batch Name', 'visible': 1, 'sortable': true},
        {'dbName': 'cmssw_release', 'displayName': 'CMSSW Release', 'visible': 1, 'sortable': true},
        {'dbName': 'cpu_cores', 'displayName': 'CPU Cores', 'visible': 1, 'sortable': true},
        {'dbName': 'matrix', 'displayName': 'Matrix', 'visible': 1, 'sortable': true},
        {'dbName': 'memory', 'displayName': 'Memory', 'visible': 1, 'sortable': true},
        {'dbName': 'notes', 'displayName': 'Notes', 'visible': 1},
        {'dbName': '_workflow', 'displayName': 'Workflow', 'visible': 1, 'sortable': true},
        {'dbName': 'campaign_timestamp', 'displayName': 'Campaign', 'visible': 0, 'sortable': true},
        {'dbName': 'fragment', 'displayName': 'Fragment', 'visible': 0},
        {'dbName': '_gpu', 'displayName': 'GPU', 'visible': 0},
        {'dbName': 'history', 'displayName': 'History', 'visible': 0, 'sortable': true},
        {'dbName': 'label', 'displayName': 'Label', 'visible': 0, 'sortable': true},
        {'dbName': 'output_datasets', 'displayName': 'Output Datasets', 'visible': 0},
        {'dbName': 'sample_tag', 'displayName': 'Sample Tag', 'visible': 0, 'sortable': true},
        {'dbName': 'size_per_event', 'displayName': 'Size per Event', 'visible': 0, 'sortable': true},
        {'dbName': 'steps', 'displayName': 'Steps', 'visible': 0},
        {'dbName': 'time_per_event', 'displayName': 'Time per Event', 'visible': 0, 'sortable': true},
        {'dbName': 'workflows', 'displayName': 'Workflows (jobs in ReqMgr2)', 'visible': 0},
      ],
      headers: [],
      dataItems: [],
      selectedItems: [],
      loading: false,
      itemsPerPage: 1,  // If initial value is 0, table does not appear after update
      totalItems: 0,
      dialog: {
        visible: false,
        title: '',
        description: '',
        cancel: undefined,
        ok: undefined,
      },
      errorDialog: {
        visible: false,
        title: '',
        description: ''
      },
      isDev: false,
      optionsSync: {},
    }
  },
  watch: {
    optionsSync: {
      handler (newOptions, oldOptions) {
        if (!oldOptions.sortBy || !oldOptions.sortDesc || !newOptions.sortBy || !newOptions.sortDesc) {
          return;
        }
        let oldSortBy = undefined;
        if (oldOptions.sortBy.length) {
          oldSortBy = oldOptions.sortBy[0];
        }
        let oldSortAsc = undefined;
        if (oldOptions.sortDesc.length) {
          oldSortAsc = oldOptions.sortDesc[0];
        }
        let sortBy = undefined;
        if (newOptions.sortBy.length) {
          sortBy = newOptions.sortBy[0];
        }
        let sortAsc = undefined;
        if (newOptions.sortDesc.length) {
          sortAsc = newOptions.sortDesc[0];
        }
        if (oldSortBy === sortBy && oldSortAsc === sortAsc) {
          return;
        }
        let query = Object.assign({}, this.$route.query);
        if (sortBy !== undefined) {
          if (sortBy == '_workflow') {
            query['sort'] = 'workflow_id';
          } else if (sortBy == 'history') {
            query['sort'] = 'created_on';
          } else {
            query['sort'] = sortBy;
          }
        } else {
          delete query['sort']
        }
        if (sortAsc !== undefined) {
          query['sort_asc'] = sortAsc ? 'true' : 'false';
        } else {
          delete query['sort_asc']
        }
        this.$router.replace({query: query}).catch(() => {});
        this.fetchObjects();
      },
      deep: true,
    },
  },
  created () {
    this.clearDialog();
    this.isDev = document.location.origin.includes('dev');
    let query = Object.assign({}, this.$route.query);
    if ('sort' in query) {
      this.optionsSync.sortBy = [query['sort']];
    }
    if ('sort_asc' in query) {
      this.optionsSync.sortDesc = [query['sort_asc'] == 'true'];
    }
  },
  methods: {
    fetchObjects () {
      let component = this;
      this.loading = true;
      let query = this.$route.query;
      let queryParams = '';
      Object.keys(query).forEach(k => {
        if (k != 'shown') {
          queryParams += '&' + k + '=' + query[k];
        }
      });
      axios.get('api/search?db_name=relvals' + queryParams).then(response => {
        component.dataItems = response.data.response.results.map(function (x) { x._actions = undefined; return x});
        component.dataItems.forEach(item => {
          if (item.workflows && item.workflows.length) {
            const lastWorkflow = item.workflows[item.workflows.length - 1];
            if (lastWorkflow.output_datasets) {
              lastWorkflow.output_datasets.forEach(ds => {
                ds.datatier = ds.name.split('/').pop();
                ds.completed = (lastWorkflow.total_events > 0 ? (ds.events / lastWorkflow.total_events * 100) : 0).toFixed(2);
                ds.niceEvents = ds.events.toLocaleString('en-US');
              });
            }
          }
        });
        component.totalItems = response.data.response.total_rows;
        component.loading = false;
      }).catch(error => {
        component.loading = false;
        component.clearDialog();
        component.showError("Error fetching RelVals", component.getError(error));
      });
    },
    updateTableColumns: function(columns, headers) {
      this.columns = columns;
      this.headers = headers;
    },
    onPaginatorUpdate: function(page, itemsPerPage) {
      this.itemsPerPage = itemsPerPage;
      this.fetchObjects();
    },
    clearDialog: function() {
      this.dialog.visible = false;
      this.dialog.title = '';
      this.dialog.description = '';
      this.dialog.ok = function() {};
      this.dialog.cancel = function() {};
    },
    clearErrorDialog: function() {
      this.errorDialog.visible = false;
      this.errorDialog.title = '';
      this.errorDialog.description = '';
    },
    showError: function(title, description) {
      this.clearErrorDialog();
      this.errorDialog.title = title;
      this.errorDialog.description = description;
      this.errorDialog.visible = true;
    },
    showDeleteDialog: function(relval) {
      let component = this;
      this.dialog.title = "Delete " + relval.prepid + "?";
      this.dialog.description = "Are you sure you want to delete " + relval.prepid + " ticket?";
      this.dialog.ok = function() {
        component.loading = true;
        axios.delete('api/relvals/delete', {data: {'prepid': relval.prepid}}).then(() => {
          component.clearDialog();
          component.fetchObjects();
        }).catch(error => {
          component.loading = false;
          component.clearDialog();
          component.showError("Error deleting relval", component.getError(error));
        });
      }
      this.dialog.cancel = this.clearDialog;
      this.dialog.visible = true;
    },
    deleteRelVals: function(relvals) {
      let component = this;
      this.dialog.title = "Delete " + relvals.length + " RelVals?";
      this.dialog.description = "Are you sure you want to delete " + relvals.length + " RelVals?";
      this.dialog.ok = function() {
        component.loading = true;
        axios.delete('api/relvals/delete', {data: relvals.slice()}).then(() => {
          component.clearDialog();
          component.fetchObjects();
          component.selectedItems = [];
        }).catch(error => {
          component.loading = false;
          component.clearDialog();
          component.showError("Error deleting RelVals", component.getError(error));
          component.selectedItems =  [];
        });
      }
      this.dialog.cancel = this.clearDialog;
      this.dialog.visible = true;
    },
    nextStatus: function (relvals) {
      let component = this;
      const submit = function () {
        component.clearDialog();
        component.loading = true;
        axios.post('api/relvals/next_status', relvals.slice()).then(() => {
          component.fetchObjects();
          component.selectedItems = [];
        }).catch(error => {
          component.loading = false;
          component.clearDialog();
          component.showError("Error moving RelVal to next status", component.getError(error));
          component.selectedItems = [];
        });
      }
      let showDataWarning = false;
      // Iterate through all RelVals and see if there are any that have --data and are approved
      for (let relval of relvals) {
        for (let step of relval.steps) {
          if (step.driver.data && relval.status == 'approved') {
            showDataWarning = true;
            break;
          }
        }
        if (showDataWarning) {
          break;
        }
      }
      if (showDataWarning) {
        this.dialog.title = "Make sure RelVal datasets are available on disk";
        this.dialog.description = "Please make sure that data RelVals have required dataset blocks on a disk. List of datasets <a href='https://twiki.cern.ch/twiki/bin/view/CMS/Run2DataForRelVals' target='_blank'>can be found on TWiki</a>";
        this.dialog.ok = submit;
        this.dialog.cancel = this.clearDialog;
        this.dialog.visible = true;
      } else {
        submit();
      }
    },
    previousStatus: function(relvals) {
      let component = this;
      if (relvals.length > 1) {
        this.dialog.title = "Move " + relvals.length + " RelVals to previous status?";
        this.dialog.description = "Are you sure you want to move " + relvals.length + " RelVals to previous status?";
      } else {
        this.dialog.title = "Move " + relvals[0].prepid + " RelVal to previous status?";
        this.dialog.description = "Are you sure you want to move " + relvals[0].prepid + " RelVal to previous status?";
      }
      this.dialog.ok = function() {
        component.loading = true;
        axios.post('api/relvals/previous_status', relvals.slice()).then(() => {
          component.clearDialog();
          component.fetchObjects();
          component.selectedItems = [];
        }).catch(error => {
          component.loading = false;
          component.clearDialog();
          component.showError("Error moving RelVal to previous status", component.getError(error));
          component.selectedItems = [];
        });
      }
      this.dialog.cancel = this.clearDialog;
      this.dialog.visible = true;
    },
    updateWorkflows: function(relvals) {
      let component = this;
      this.loading = true;
      axios.post('api/relvals/update_workflows', relvals.slice()).then(() => {
        component.fetchObjects();
        component.selectedItems =  [];
      }).catch(error => {
        component.loading = false;
        component.clearDialog();
        component.showError("Error updating RelVal info", component.getError(error));
        component.selectedItems = [];
      });
    },
    editRelVals: function(relvals) {
      let prepids = relvals.map(x => x['prepid']);
      window.location = 'relvals/edit_many?prepid=' + prepids.join(',');
    },
    niceDate: function (time) {
      if (!time) {
        time = 0;
      }
      return dateFormat(new Date(time * 1000), 'yyyy-mm-dd HH:MM:ss')
    },
    openPmpMany: function(relvals) {
      let prepids = relvals.map(x => x['prepid']);
      let url = 'https://cms-pdmv.cern.ch/pmp/historical?r=' + prepids.join(',');
      window.open(url, '_blank');
    },
    stepSteps: function(step) {
      return step.driver.step.map(x => x.split(':')[0]).join(',')
    }
  }
}
</script>

<style scoped>
.bar {
  line-height:10px;
  height: 10px;
  display: inline-block;
  max-width: 100%;
  background-color: #2C3E50;
}

.production-bar {
  background-color:#F39C12;
}

.valid-bar {
  background-color:#3498db;
}

.invalid-bar {
  background-color:#C0392B;
}

.deleted-bar {
  background-color:#E74C3C;
}

.gray-bar {
  width: 100px;
  background-color: #BDC3C7;
  display: inline-block;
  line-height:10px;
  height: 10px;
  font-size: 0;
  overflow: hidden;
  margin-right: 4px;
}

.valid-type {
  color: green;
}

.production-type, .invalid-type, .deleted-type, .deprecated-type {
  color: red;
}

.none-type {
  color: #8A8A8A;
}

.zebra-datasets {
  margin-top: -5px;
}

.zebra-datasets > li > div {
  padding-top: 5px;
  padding-bottom: 5px;
  line-height: 1;
}

.zebra-datasets > li:nth-child(2n) > div {
  background: #f5f5fc;
  background: linear-gradient(90deg, #f5f5fc 0%, rgba(0,212,255,0) 100%);
  padding-left: 24px;
  margin-left: -24px;
}
</style>

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
                      disable-sort
                      hide-default-footer
                      class="elevation-1"
                      show-select
                      item-key="prepid"
                      v-model="selectedItems">
          <template v-slot:item._actions="{ item }">
            <a :href="'relvals/edit?prepid=' + item.prepid" v-if="role('manager')">Edit</a>&nbsp;
            <a style="text-decoration: underline;" @click="deleteRelVals([item])" v-if="role('manager')">Delete</a>&nbsp;
            <a :href="'api/relvals/get_cmsdriver/' + item.prepid" title="Show cmsDriver.py command for this RelVal">cmsDriver</a>&nbsp;
            <a :href="'api/relvals/get_dict/' + item.prepid" title="Show JSON dictionary for ReqMgr2">Job dict</a>&nbsp;
            <a :href="'api/relvals/get_config_upload/' + item.prepid" title="Show config upload script">Config upload</a>&nbsp;
            <a style="text-decoration: underline;" @click="previousStatus([item])" v-if="role('manager') && item.status != 'new'" title="Move to previous status">Previous</a>&nbsp;
            <a style="text-decoration: underline;" @click="nextStatus([item])" v-if="role('manager')" title="Move to next status">Next</a>&nbsp;
            <a style="text-decoration: underline;" @click="updateWorkflows([item])" v-if="role('manager') && item.status == 'submitted'" title="Update RelVal information from Stats2">Update from Stats2</a>&nbsp;
            <a target="_blank" :href="'https://cms-pdmv.cern.ch/stats?prepid=' + item.prepid" v-if="item.status == 'submitted' || item.status == 'done'" title="Show workflows of this RelVal in Stats2">Stats2</a>         
          </template>
          <template v-slot:item.prepid="{ item }">
            <a :href="'relvals?prepid=' + item.prepid">{{item.prepid}}</a>
          </template>
          <template v-slot:item.history="{ item }">
            <HistoryCell :data="item.history"/>
          </template>
          <template v-slot:item.notes="{ item }">
            <pre v-if="item.notes.length" class="notes">{{item.notes}}</pre>
          </template>
          <template v-slot:item.memory="{ item }">
            {{item.memory}} MB
          </template>
          <template v-slot:item.steps="{ item }">
            <StepsCell :data="item.steps"/>
          </template>
          <template v-slot:item._workflow="{ item }">
            {{item.workflow_id}} <span v-if="item.workflow_name">({{item.workflow_name}})</span>
          </template>
          <template v-slot:item.workflows="{ item }">
            <ol>
              <li v-for="(workflow, index) in item.workflows" :key="workflow.name">
                <a target="_blank" title="Open workflow in ReqMgr2" :href="'https://cmsweb.cern.ch/reqmgr2/fetch?rid=' + workflow.name">{{workflow.name}}</a>&nbsp;
                <a target="_blank" title="Open workflow in Stats2" :href="'https://cms-pdmv.cern.ch/stats?workflow_name=' + workflow.name">Stats2</a>&nbsp;
                <span v-if="workflow.status_history && workflow.status_history.length > 0">
                  <small>type:</small> {{workflow.type}}
                  <small>status:</small> {{workflow.status_history[workflow.status_history.length - 1].status}}
                </span>
                <ul v-if="index == item.workflows.length - 1">
                  <li v-for="dataset in workflow.output_datasets" :key="dataset.name">
                    <a target="_blank" title="Open dataset in DAS" :href="makeDASLink(dataset.name)">{{dataset.name}}</a>&nbsp;
                    <small>events:</small> {{dataset.events}}
                    <small>type:</small> {{dataset.type}}
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
          <template v-slot:item.campaign="{ item }">
            <a :href="'relvals?campaign=' + item.campaign" :title="'Show all RelVals with ' + item.campaign + ' campaign'">{{item.campaign}}</a>
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
          {{dialog.description}}
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
      <a :href="'relvals/edit'" v-if="role('manager') && !selectedItems.length">New RelVal</a>
      <span v-if="role('manager') && selectedItems.length">Selected items ({{selectedItems.length}}) actions:</span>
      <a v-if="role('manager') && selectedItems.length" @click="deleteRelVals(selectedItems)" title="Delete selected RelVals">Delete</a>
      <a v-if="role('manager') && selectedItems.length" @click="previousStaus(selectedItems)" title="Move selected RelVals to previous status">Previous</a>
      <a v-if="role('manager') && selectedItems.length" @click="nextStatus(selectedItems)" title="Move selected RelVals to next status">Next</a>
      <a v-if="role('manager') && selectedItems.length" @click="updateWorkflows(selectedItems)" title="Update selected RelVals' information from Stats2">Update from Stats2</a>
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
        {'dbName': 'prepid', 'displayName': 'PrepID', 'visible': 1},
        {'dbName': '_actions', 'displayName': 'Actions', 'visible': 1},
        {'dbName': 'status', 'displayName': 'Status', 'visible': 1},
        {'dbName': 'campaign', 'displayName': 'Campaign', 'visible': 1},
        {'dbName': 'cpu_cores', 'displayName': 'CPU Cores', 'visible': 1},
        {'dbName': 'matrix', 'displayName': 'Matrix', 'visible': 1},
        {'dbName': 'memory', 'displayName': 'Memory', 'visible': 1},
        {'dbName': 'notes', 'displayName': 'Notes', 'visible': 1},
        {'dbName': '_workflow', 'displayName': 'Workflow', 'visible': 1},
        {'dbName': 'history', 'displayName': 'History', 'visible': 0},
        {'dbName': 'label', 'displayName': 'Label', 'visible': 0},
        {'dbName': 'output_datasets', 'displayName': 'Output Datasets', 'visible': 0},
        {'dbName': 'sample_tag', 'displayName': 'Sample Tag', 'visible': 0},
        {'dbName': 'size_per_event', 'displayName': 'Size per Event', 'visible': 0},
        {'dbName': 'steps', 'displayName': 'Steps', 'visible': 0},
        {'dbName': 'time_per_event', 'displayName': 'Time per Event', 'visible': 0},
        {'dbName': 'workflows', 'displayName': 'Workflows (jobs)', 'visible': 0},
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
      }
    }
  },
  created () {
    this.clearDialog();
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
        this.dialog.description = "Please make sure that data RelVals have required dataset blocks on a disk";
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
  }
}
</script>

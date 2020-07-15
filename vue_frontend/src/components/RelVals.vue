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
                      :mobile-breakpoint=NaN
                      :loading="loading"
                      disable-sort
                      hide-default-footer
                      class="elevation-1"
                      show-select
                      item-key="prepid"
                      v-model="selectedItems">
          <template v-slot:item._actions="{ item }">
            <a :href="'relvals/edit?prepid=' + item.prepid" v-if="role('manager')">Edit</a>&nbsp;
            <a style="text-decoration: underline;" @click="showDeleteDialog(item)" v-if="role('manager')">Delete</a>&nbsp;
            <a :href="'api/relvals/get_cmsdriver/' + item.prepid" title="Show cmsDriver.py command for this RelVal">cmsDriver</a>&nbsp;
            <a :href="'api/relvals/get_dict/' + item.prepid" title="Show JSON dictionary for ReqMgr2">Job dict</a>&nbsp;
            <a :href="'api/relvals/get_config_upload/' + item.prepid" title="Show config upload script">Config upload</a>&nbsp;
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
          <template v-slot:item.cmssw_release="{ item }">
            {{item.cmssw_release.replace('_', ' ').replace(/_/g, '.')}}
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
          <v-btn small class="mr-1 mb-1" color="primary" @click="dialog.cancel">
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
          {{errorDialog.description}}
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
      <a v-if="role('manager') && selectedItems.length" @click="deleteManyRelVals(selectedItems)" title="Delete selected RelVals">Delete</a>
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
export default {
  components: {
    ColumnSelector,
    Paginator,
    HistoryCell,
    StepsCell
  },
  mixins: [roleMixin],
  data () {
    return {
      databaseName: undefined,
      columns: [
        {'dbName': 'prepid', 'displayName': 'PrepID', 'visible': 1},
        {'dbName': '_actions', 'displayName': 'Actions', 'visible': 1},
        {'dbName': 'status', 'displayName': 'Status', 'visible': 1},
        {'dbName': 'campaign', 'displayName': 'Campaign', 'visible': 1},
        {'dbName': 'cmssw_release', 'displayName': 'CMSSW Release', 'visible': 1},
        {'dbName': 'cpu_cores', 'displayName': 'CPU Cores', 'visible': 1},
        {'dbName': 'relval_set', 'displayName': 'RelVal Set', 'visible': 1},
        {'dbName': '_workflow', 'displayName': 'Workflow', 'visible': 1},
        {'dbName': 'memory', 'displayName': 'Memory', 'visible': 1},
        {'dbName': 'notes', 'displayName': 'Notes', 'visible': 1},
        {'dbName': 'conditions_globaltag', 'displayName': 'GlobalTag', 'visible': 0},
        {'dbName': 'history', 'displayName': 'History', 'visible': 0},
        {'dbName': 'sample_tag', 'displayName': 'Sample Tag', 'visible': 0},
        {'dbName': 'steps', 'displayName': 'Steps', 'visible': 0},
        {'dbName': 'label', 'displayName': 'Label', 'visible': 0},
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
          component.showError("Error deleting relval", error.response.data.message);
        });
      }
      this.dialog.cancel = function() {
        component.clearDialog();
      }
      this.dialog.visible = true;
    },
    deleteManyRelVals: function(relvals) {
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
          component.showError("Error deleting RelVals", error.response.data.message);
          component.selectedItems =  [];
        });
      }
      this.dialog.cancel = function() {
        component.clearDialog();
      }
      this.dialog.visible = true;
    },
  }
}
</script>

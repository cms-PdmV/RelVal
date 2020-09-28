<template>
  <div style="height: calc(100vh - 118px); overflow: auto;">
    <div style="display: flex;">
      <div style="flex: 1 1 auto;">
        <div>
          <div style="width: calc(100vw - 32px); position: sticky; left: 16px;">
            <h1 class="page-title">Tickets</h1>
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
                      class="elevation-1">
          <template v-slot:item._actions="{ item }">
            <a :href="'tickets/edit?prepid=' + item.prepid" v-if="role('manager')" title="Edit ticket">Edit</a>&nbsp;
            <a style="text-decoration: underline;" @click="showDeleteDialog(item)" v-if="role('manager')" title="Delete ticket">Delete</a>&nbsp;
            <a :href="'tickets/edit?clone=' + item.prepid" v-if="role('manager')" title="Clone ticket">Clone</a>&nbsp;
            <a style="text-decoration: underline;" @click="showCreateRelValsDialog(item)" v-if="role('manager') && item.status == 'new'" title="Create RelVals from this ticket">Create RelVals</a>&nbsp;
            <a :href="'relvals?ticket=' + item.prepid" v-if="item.created_relvals && item.created_relvals.length > 0" title="Show all RelVals created from this ticket">Show RelVals</a>&nbsp;
          </template>
          <template v-slot:item.prepid="{ item }">
            <a :href="'tickets?prepid=' + item.prepid" title="Show only this ticket">{{item.prepid}}</a>
          </template>
          <template v-slot:item.status="{ item }">
            <a :href="'tickets?status=' + item.status" :title="'Show all tickets with status ' + item.status">{{item.status}}</a>
          </template>
          <template v-slot:item.matrix="{ item }">
            <a :href="'tickets?matrix=' + item.matrix" :title="'Show all tickets with ' + item.matrix + ' matrix'">{{item.matrix}}</a>
          </template>
          <template v-slot:item.sample_tag="{ item }">
            <a :href="'tickets?sample_tag=' + item.sample_tag" :title="'Show all tickets with ' + item.sample_tag + ' sample tag'">{{item.sample_tag}}</a>
          </template>
          <template v-slot:item.label="{ item }">
            <a :href="'tickets?label=' + item.label" :title="'Show all tickets with ' + item.label + ' label'">{{item.label}}</a>
          </template>
          <template v-slot:item.history="{ item }">
            <HistoryCell :data="item.history"/>
          </template>
          <template v-slot:item.memory="{ item }">
            {{item.memory}} MB
          </template>
          <template v-slot:item.notes="{ item }">
            <pre v-if="item.notes.length" v-html="sanitize(item.notes)" class="notes" v-linkified></pre>
          </template>
          <template v-slot:item.workflow_ids="{ item }">
            <span v-if="item.workflow_ids.length">{{item.workflow_ids.length}} workflows: <small>{{item.workflow_ids.join(', ')}}</small></span>
          </template>
          <template v-slot:item.cmssw_release="{ item }">
            <a :href="'tickets?cmssw_release=' + item.cmssw_release" :title="'Show all tickets with ' + item.cmssw_release">{{(item.cmssw_release || '').replace('_', ' ').replace(/_/g, '.')}}</a>
          </template>
          <template v-slot:item.batch_name="{ item }">
            <a :href="'tickets?batch_name=' + item.batch_name" :title="'Show all tickets with ' + item.batch_name">{{item.batch_name}}</a>
          </template>
          <template v-slot:item.created_relvals="{ item }">
            <span v-if="item.created_relvals && item.created_relvals.length > 0"><a :href="'relvals?ticket=' + item.prepid">{{item.created_relvals.length}} RelVals:</a></span>
            <ul>
              <li v-for="relval in item.created_relvals" :key="relval">
                <a :href="'relvals?prepid=' + relval" :title="'Open ' + relval + ' RelVal'">{{relval}}</a>
              </li>
            </ul>
          </template>
          <template v-slot:item.recycle_gs="{ item }">
            {{item.recycle_gs ? 'Yes' : 'No'}}
          </template>
          <template v-slot:item.command="{ item }">
            <pre v-if="item.command && item.command.length" class="notes">{{item.command}}</pre>
          </template>
          <template v-slot:item._created="{ item }">
            Created by <a :href="'tickets?created_by=' + item.history[0].user" :title="'Show all tickets created by ' + item.history[0].user">{{item.history[0].user}}</a> on {{niceDate(item.history[0].time)}}
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

    <LoadingOverlay :visible="loadingCreatingRelVals"/>

    <footer>
      <a :href="'tickets/edit'" v-if="role('manager')">New ticket</a>
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
import { roleMixin } from '../mixins/UserRoleMixin.js'
import LoadingOverlay from './LoadingOverlay.vue'
import { utilsMixin } from '../mixins/UtilsMixin.js'
import dateFormat from 'dateformat'

export default {
  components: {
    ColumnSelector,
    Paginator,
    HistoryCell,
    LoadingOverlay,
  },
  mixins: [roleMixin, utilsMixin],
  data () {
    return {
      databaseName: undefined,
      columns: [
        {'dbName': 'prepid', 'displayName': 'PrepID', 'visible': 1},
        {'dbName': '_actions', 'displayName': 'Actions', 'visible': 1},
        {'dbName': 'status', 'displayName': 'Status', 'visible': 1},
        {'dbName': 'batch_name', 'displayName': 'Batch Name', 'visible': 1},
        {'dbName': 'cmssw_release', 'displayName': 'CMSSW Release', 'visible': 1},
        {'dbName': 'cpu_cores', 'displayName': 'CPU Cores', 'visible': 1},
        {'dbName': 'matrix', 'displayName': 'Matrix', 'visible': 1},
        {'dbName': 'memory', 'displayName': 'Memory', 'visible': 1},
        {'dbName': 'notes', 'displayName': 'Notes', 'visible': 1},
        {'dbName': 'recycle_gs', 'displayName': 'Recycle GS', 'visible': 1},
        {'dbName': 'workflow_ids', 'displayName': 'Workflows', 'visible': 1},
        {'dbName': 'command', 'displayName': 'Command', 'visible': 0},
        {'dbName': 'created_relvals', 'displayName': 'Created RelVals', 'visible': 0},
        {'dbName': '_created', 'displayName': 'Creation', 'visible': 0},
        {'dbName': 'history', 'displayName': 'History', 'visible': 0},
        {'dbName': 'label', 'displayName': 'Label', 'visible': 0},
        {'dbName': 'rewrite_gt_string', 'displayName': 'Rewrite GT String', 'visible': 0},
        {'dbName': 'sample_tag', 'displayName': 'Sample Tag', 'visible': 0},
      ],
      headers: [],
      dataItems: [],
      loading: false,
      loadingCreatingRelVals: false,
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
      axios.get('api/search?db_name=tickets' + queryParams).then(response => {
        component.dataItems = response.data.response.results.map(function (x) { x._actions = undefined; return x});
        component.totalItems = response.data.response.total_rows;
        component.loading = false;
      }).catch(error => {
        component.loading = false;
        component.clearDialog();
        component.showError("Error fetching tickets", component.getError(error));
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
    showDeleteDialog: function(ticket) {
      let component = this;
      this.dialog.title = "Delete " + ticket.prepid + "?";
      this.dialog.description = "Are you sure you want to delete " + ticket.prepid + " ticket?";
      this.dialog.ok = function() {
        component.loading = true;
        axios.delete('api/tickets/delete', {data: {'prepid': ticket.prepid}}).then(() => {
          component.clearDialog();
          component.fetchObjects();
        }).catch(error => {
          component.loading = false;
          component.clearDialog();
          component.showError("Error deleting ticket", component.getError(error));
        });
      }
      this.dialog.cancel = function() {
        component.clearDialog();
      }
      this.dialog.visible = true;
    },
    showCreateRelValsDialog: function(ticket) {
      let component = this;
      this.dialog.title = "Create RelVals for " + ticket.prepid + "?";
      this.dialog.description = "Are you sure you want to generate RelVals for " + ticket.prepid + " ticket? After RelVals are created, this ticket cannot be modified, additional workflows will require a new ticket.";
      this.dialog.ok = function() {
        component.loading = true;
        component.loadingCreatingRelVals = true;
        component.clearDialog();
        axios.post('api/tickets/create_relvals', {'prepid': ticket.prepid}, {timeout: 180000}).then(() => {
          component.loadingCreatingRelVals = false;
          component.loading = false;
          component.fetchObjects();
        }).catch(error => {
          component.loadingCreatingRelVals = false;
          component.loading = false;
          component.showError("Error creating RelVals", component.getError(error));
        });
      }
      this.dialog.cancel = function() {
        component.clearDialog();
      }
      this.dialog.visible = true;
    },
    niceDate: function (time) {
      return dateFormat(new Date(time * 1000), 'yyyy-mm-dd HH:MM:ss')
    },
  }
}
</script>

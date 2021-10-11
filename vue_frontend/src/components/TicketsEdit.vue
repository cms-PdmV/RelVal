<template>
  <div>
    <h1 class="page-title" v-if="creatingNew"><span class="font-weight-light">Creating</span> new ticket</h1>
    <h1 class="page-title" v-else><span class="font-weight-light">Editing ticket</span> {{prepid}}</h1>
    <v-card raised class="page-card">
      <table v-if="editableObject">
        <tr>
          <td>PrepID</td>
          <td><input type="text" v-model="editableObject.prepid" :disabled="!editingInfo.prepid"></td>
        </tr>
        <tr>
          <td>Batch name (-b)</td>
          <td><input type="text" v-model="editableObject.batch_name" placeholder="E.g. fullsim_noPU_..." :disabled="!editingInfo.batch_name"></td>
        </tr>
        <tr>
          <td>CMSSW Release</td>
          <td><input type="text" v-model="editableObject.cmssw_release" placeholder="E.g. CMSSW_11_..." :disabled="!editingInfo.cmssw_release"></td>
        </tr>
        <tr>
          <td>Command (--command)</td>
          <td><input type="text" v-model="editableObject.command" placeholder="Argument that will be added to all cmsDrivers" :disabled="!editingInfo.command"></td>
        </tr>
        <tr>
          <td>Command Steps</td>
          <td><input type="text" v-model="editableObject.command_steps" placeholder="E.g. GEN,SIM,DIGI" :disabled="!editingInfo.command_steps"></td>
        </tr>
        <tr>
          <td>CPU Cores (-t)</td>
          <td><input type="number" v-model="editableObject.cpu_cores" :disabled="!editingInfo.cpu_cores" min="1" max="8"></td>
        </tr>
        <tr>
          <td>GPU</td>
          <td>
            <select v-model="editableObject.gpu.requires" :disabled="!editingInfo.gpu">
              <option>forbidden</option>
              <option>optional</option>
              <option>required</option>
            </select>
          </td>
        </tr>
        <tr v-if="editableObject.gpu.requires != 'forbidden'">
          <td>GPU Parameters</td>
          <td>
            <table>
              <tr>
                <td>GPU Memory</td>
                <td><input type="number" v-model="editableObject.gpu.gpu_memory" :disabled="!editingInfo.gpu" min="0" max="32000" step="1000">MB</td>
              </tr>
              <tr>
                <td>CUDA Capabilities</td>
                <td><input type="text" v-model="editableObject.gpu.cuda_capabilities" placeholder="E.g. 6.0,6.1,6.2" :disabled="!editingInfo.gpu"></td>
              </tr>
              <tr>
                <td>CUDA Runtime</td>
                <td><input type="text" v-model="editableObject.gpu.cuda_runtime" :disabled="!editingInfo.gpu"></td>
              </tr>
              <tr>
                <td>GPU Name</td>
                <td><input type="text" v-model="editableObject.gpu.gpu_name" :disabled="!editingInfo.gpu"></td>
              </tr>
              <tr>
                <td>CUDA Driver Version</td>
                <td><input type="text" v-model="editableObject.gpu.cuda_driver_version" :disabled="!editingInfo.gpu"></td>
              </tr>
              <tr>
                <td>CUDA Runtime Version</td>
                <td><input type="text" v-model="editableObject.gpu.cuda_runtime_version" :disabled="!editingInfo.gpu"></td>
              </tr>
            </table>
          </td>
        </tr>
        <tr v-if="editableObject.gpu.requires != 'forbidden'">
          <td>GPU Steps</td>
          <td><input type="text" v-model="editableObject.gpu_steps" placeholder="E.g. DIGI,HLT" :disabled="!editingInfo.gpu_steps"></td>
        </tr>
        <tr>
          <td>Label (--label)</td>
          <td><input type="text" v-model="editableObject.label" placeholder="E.g. gcc8 or rsb or pmx" :disabled="!editingInfo.label"></td>
        </tr>
        <tr>
          <td>Matrix (--what)</td>
          <td>
            <select v-model="editableObject.matrix" :disabled="!editingInfo.matrix">
              <option>standard</option>
              <option>upgrade</option>
              <option>generator</option>
              <option>pileup</option>
              <option>premix</option>
              <option>extendedgen</option>
              <option>gpu</option>
            </select>
          </td>
        </tr>
        <tr>
          <td>Memory</td>
          <td><input type="number" v-model="editableObject.memory" :disabled="!editingInfo.memory" min="0" max="32000" step="1000">MB</td>
        </tr>
        <tr>
          <td>Notes</td>
          <td><textarea v-model="editableObject.notes" placeholder="E.g. Goals, comments, links to TWiki and HN" :disabled="!editingInfo.notes"></textarea></td>
        </tr>
        <tr>
          <td>Recycle GS (-i all)</td>
          <td><input type="checkbox" v-model="editableObject.recycle_gs" :disabled="!editingInfo.recycle_gs"/></td>
        </tr>
        <tr>
          <td>Recycle input for step</td>
          <td><input type="text" v-model="editableObject.recycle_step_input" placeholder="E.g. DIGI or RECO" :disabled="!editingInfo.recycle_step_input"></td>
        </tr>
        <tr>
          <td>Rewrite GT String</td>
          <td>
            <input type="text" v-model="editableObject.rewrite_gt_string" placeholder="E.g. CMSSW_10_3_0_pre5-103X_upgrade2018_realistic_v7-v1" :disabled="!editingInfo.rewrite_gt_string">
            <small v-if="editableObject.rewrite_gt_string"><br>Preview: /PrimaryDataset/<span style="color: red">{{editableObject.rewrite_gt_string}}</span>/DATATIER</small>
          </td>
        </tr>
        <tr>
          <td>Sample Tag</td>
          <td><input type="text" v-model="editableObject.sample_tag" placeholder="E.g. Run2, Run3, Phase2, HIN, GEN, ..." :disabled="!editingInfo.sample_tag"></td>
        </tr>
        <tr>
          <td>SCRAM Arch</td>
          <td><input type="text" v-model="editableObject.scram_arch" placeholder="If empty, uses default value of the release" :disabled="!editingInfo.scram_arch"></td>
        </tr>
        <tr>
          <td>Streams (--nStreams)</td>
          <td>
            <input type="number" v-model="editableObject.n_streams" min="0" max="16" step="1" :disabled="!editingInfo.n_streams">
            <br>
            <small style="opacity: 0.5">If number of streams is 0, default value will be used</small>
          </td>
        </tr>
        <tr>
          <td>Workflow IDs ({{workflowListLength(editableObject.workflow_ids)}})</td>
          <td><textarea v-model="editableObject.workflow_ids" :placeholder="'Comma or newline separated workflow IDs, e.g. \n136.801,136.802 \n1302.181 \n10848'" :disabled="!editingInfo.workflow_ids"></textarea></td>
        </tr>
      </table>
      <v-btn small class="mr-1 mt-1" color="primary" @click="save()">Save</v-btn>
      <v-btn small class="mr-1 mt-1" color="error" @click="cancel()">Cancel</v-btn>
    </v-card>
    <LoadingOverlay :visible="loading"/>
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
          <v-btn small class="mr-1 mb-1" color="primary" @click="clearErrorDialog()">
            Dismiss
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

<script>

import axios from 'axios'
import { utilsMixin } from '../mixins/UtilsMixin.js'
import LoadingOverlay from './LoadingOverlay.vue'

export default {
  name: 'TicketsEdit',
  components: {
    LoadingOverlay,
  },
  mixins: [
    utilsMixin
  ],
  data () {
    return {
      prepid: undefined,
      editableObject: undefined,
      editingInfo: {},
      loading: true,
      creatingNew: true,
      errorDialog: {
        visible: false,
        title: '',
        description: '',
      }
    }
  },
  created () {
    let query = Object.assign({}, this.$route.query);
    if (query.prepid && query.prepid.length) {
      this.prepid = query.prepid;
    } else {
      this.prepid = '';
    }
    this.creatingNew = this.prepid.length == 0;
    this.loading = true;
    let component = this;
    axios.get('api/tickets/get_editable/' + this.prepid).then(response => {
      if (query.clone && query.clone.length) {
        axios.get('api/tickets/get_editable/' + query.clone).then(templateResponse => {
          templateResponse.data.response.object.prepid = response.data.response.object.prepid;
          templateResponse.data.response.object.history = response.data.response.object.history;
          templateResponse.data.response.object.status = response.data.response.object.status;
          templateResponse.data.response.object.created_relvals = response.data.response.object.created_relvals;
          component.editableObject = templateResponse.data.response.object;
          component.editableObject.workflow_ids = component.editableObject.workflow_ids.filter(Boolean).join('\n');
          component.editableObject.command_steps = component.editableObject.command_steps.filter(Boolean).join(',');
          component.editableObject.gpu.cuda_capabilities = component.editableObject.gpu.cuda_capabilities.filter(Boolean).join(',');
          component.editingInfo = response.data.response.editing_info;
          component.loading = false;
        }).catch(error => {
          component.loading = false;
          component.showError('Error fetching editing information', component.getError(error));
        });
      } else {
        component.editableObject = response.data.response.object;
        component.editableObject.workflow_ids = component.editableObject.workflow_ids.filter(Boolean).join('\n');
        component.editableObject.command_steps = component.editableObject.command_steps.filter(Boolean).join(',');
        component.editableObject.gpu.cuda_capabilities = component.editableObject.gpu.cuda_capabilities.filter(Boolean).join(',');
        component.editingInfo = response.data.response.editing_info;
        component.loading = false;
      }
    }).catch(error => {
      component.loading = false;
      component.showError('Error fetching editing information', component.getError(error));
    });
  },
  methods: {
    save: function() {
      this.loading = true;
      let editableObject = this.makeCopy(this.editableObject);
      editableObject.notes = editableObject.notes.trim();
      editableObject.workflow_ids = this.cleanSplit(editableObject.workflow_ids);
      editableObject.command_steps = this.cleanSplit(editableObject.command_steps);
      editableObject.gpu.cuda_capabilities = this.cleanSplit(editableObject.gpu.cuda_capabilities);
      let httpRequest;
      if (this.creatingNew) {
        httpRequest = axios.put('api/tickets/create', editableObject);
      } else {
        httpRequest = axios.post('api/tickets/update', editableObject);
      }
      let component = this;
      httpRequest.then(response => {
        component.loading = false;
        window.location = 'tickets?prepid=' + response.data.response.prepid;
      }).catch(error => {
        component.loading = false;
        component.showError('Error saving ticket', component.getError(error));
      });
    },
    cancel: function() {
      if (this.creatingNew) {
        window.location = 'tickets';
      } else {
        window.location = 'tickets?prepid=' + this.prepid;
      }
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
    workflowListLength: function(list) {
      return this.cleanSplit(list).length;
    }
  }
}
</script>

<template>
  <div>
    <h1 v-if="creatingNew">Creating new RelVal</h1>
    <h1 v-else>Editing {{editableObject.prepid}}</h1>
    <v-card raised class="editPageCard">
      <table v-if="editableObject">
        <tr>
          <td>PrepID</td>
          <td><input type="text" v-model="editableObject.prepid" :disabled="!editingInfo.prepid"></td>
        </tr>
        <tr>
          <td>CMSSW Release</td>
          <td><input type="text" v-model="editableObject.cmssw_release" :disabled="!editingInfo.cmssw_release"></td>
        </tr>
        <tr>
          <td>Extension Number</td>
          <td>
            <select v-model="editableObject.extension_number" :disabled="!editingInfo.extension_number">
              <option v-for="i in 10" :key="i" :value="i - 1">{{i - 1}}</option>
            </select>
          </td>
        </tr>
        <tr>
          <td>GlobalTag</td>
          <td><input type="text" v-model="editableObject.conditions_globaltag" :disabled="!editingInfo.conditions_globaltag"></td>
        </tr>
        <tr>
          <td>Notes</td>
          <td><textarea v-model="editableObject.notes" :disabled="!editingInfo.notes"></textarea></td>
        </tr>
        <tr>
          <td>Processing String</td>
          <td><input type="text" v-model="editableObject.processing_string" :disabled="!editingInfo.processing_string"></td>
        </tr>
        <tr>
          <td>RelVal set</td>
          <td>
            <select v-model="editableObject.relval_set" :disabled="!editingInfo.relval_set">
              <option>standard</option>
              <option>upgrade</option>
            </select>
          </td>
        </tr>
        <tr>
          <td>Reuse GEN-SIM</td>
          <td><v-checkbox v-model="editableObject.reuse_gensim" :disabled="!editingInfo.reuse_gensim" hide-details class="shrink checkbox-margin"></v-checkbox></td>
        </tr>
        <tr>
          <td>Sample Tag</td>
          <td><input type="text" v-model="editableObject.sample_tag" :disabled="!editingInfo.sample_tag"></td>
        </tr>
        <tr v-if="editableObject.steps">
          <td>Steps ({{listLength(editableObject.steps)}})</td>
          <td>
            <div v-for="(step, index) in editableObject.steps" :key="index">
              <h3>Step {{index + 1}}</h3>
              <input type="radio" v-model="step.step_type" :name="'step' + index" :value="'input'">Input Step
              <input type="radio" v-model="step.step_type" :name="'step' + index" :value="'driver'">Driver Step
              <table v-if="step.step_type == 'input'">
                <tr>
                  <td>Dataset</td><td><input type="text" v-model="step.input.dataset" :disabled="!editingInfo.steps"></td>
                </tr>
                <tr>
                  <td>Lumisection</td><td><input type="text" v-model="step.input.lumisection" :disabled="!editingInfo.steps"></td>
                </tr>
              </table>
              <table v-else>
                <tr>
                  <td>--conditions</td><td><input type="text" v-model="step.arguments.conditions" :disabled="!editingInfo.steps"></td>
                </tr>
                <tr>
                  <td>--customise</td><td><input type="text" v-model="step.arguments.customise" :disabled="!editingInfo.steps"></td>
                </tr>
                <tr>
                  <td>--datatier</td><td><input type="text" v-model="step.arguments.datatier" :disabled="!editingInfo.steps"></td>
                </tr>
                <tr>
                  <td>--era</td><td><input type="text" v-model="step.arguments.era" :disabled="!editingInfo.steps"></td>
                </tr>
                <tr>
                  <td>--eventcontent</td><td><input type="text" v-model="step.arguments.eventcontent" :disabled="!editingInfo.steps"></td>
                </tr>
                <tr>
                  <td>--filein</td><td><input type="text" v-model="step.arguments.filein" :disabled="!editingInfo.steps"></td>
                </tr>
                <tr>
                  <td>--fileout</td><td><input type="text" v-model="step.arguments.fileout" :disabled="!editingInfo.steps"></td>
                </tr>
                <tr>
                  <td>--process</td><td><input type="text" v-model="step.arguments.process" :disabled="!editingInfo.steps"></td>
                </tr>
                <tr>
                  <td>--step</td><td><input type="text" v-model="step.arguments.step" :disabled="!editingInfo.steps"></td>
                </tr>
                <tr>
                  <td>--scenario</td>
                  <td>
                    <select v-model="step.arguments.scenario" :disabled="!editingInfo.steps">
                      <option></option>
                      <option>pp</option>
                      <option>cosmics</option>
                      <option>nocoll</option>
                      <option>HeavyIons</option>
                    </select>
                    {{step.arguments.scenario}}
                  </td>
                </tr>
              </table>
              <v-btn small class="mr-1 mb-1" color="error" @click="deleteStep(index)">Delete step {{index + 1}}</v-btn>
              <hr>
            </div>
            <v-btn small class="mr-1 mb-1 mt-1" color="primary" @click="addStep()">Add step {{listLength(editableObject.steps) + 1}}</v-btn>
          </td>
        </tr>
        <tr>
          <td>Workflow ID</td>
          <td><input type="number" min="1" v-model="editableObject.workflow_id" :disabled="!editingInfo.workflow_id"></td>
        </tr>
      </table>
      <v-btn small class="mr-1 mb-1" color="primary" @click="save()">Save</v-btn>
    </v-card>
    <v-overlay :absolute="false"
               :opacity="0.95"
               :z-index="3"
               :value="loading"
               style="text-align: center">
      <v-progress-circular indeterminate color="primary"></v-progress-circular>
      <br>Please wait...
    </v-overlay>
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
export default {
  components: {
  },
  data () {
    return {
      prepid: undefined,
      editableObject: {},
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
    this.loading = true;
    let query = Object.assign({}, this.$route.query);
    this.prepid = query['prepid'];
    this.creatingNew = this.prepid === undefined;
    let component = this;
    axios.get('api/relvals/get_editable' + (this.creatingNew ? '' : ('/' + this.prepid))).then(response => {
      for (let i = 0; i < response.data.response.object.steps.length; i++) {
        if (Object.keys(response.data.response.object.steps[i].input).length) {
          response.data.response.object.steps[i].step_type = 'input';
          response.data.response.object.steps[i].input.lumisection = JSON.stringify(response.data.response.object.steps[i].input.lumisection);
        } else {
          response.data.response.object.steps[i].step_type = 'driver';
        }
      }
      component.editableObject = response.data.response.object;
      component.editingInfo = response.data.response.editing_info;
      component.loading = false;
    });
  },
  methods: {
    save: function() {
      let editableObject = JSON.parse(JSON.stringify(this.editableObject))
      let component = this;
      editableObject['notes'] = editableObject['notes'].trim();
      for (let i = 0; i < editableObject.steps.length; i++) {
        if (editableObject.steps[i].step_type == 'input') {
          editableObject.steps.arguments = {};
          editableObject.steps[i].input.lumisection = JSON.parse(editableObject.steps[i].input.lumisection);
        } else {
          editableObject.steps[i].input = {};
        }
      }
      let httpRequest;
      this.loading = true;
      if (this.creatingNew) {
        httpRequest = axios.put('api/relvals/create', editableObject)
      } else {
        httpRequest = axios.post('api/relvals/update', editableObject)
      }
      httpRequest.then(response => {
        component.loading = false;
        window.location = 'relvals?prepid=' + response.data.response.prepid;
      }).catch(error => {
        component.loading = false;
        this.showError('Error saving relval', error.response.data.message)
      });
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
    listLength(l) {
      if (!l) {
        return 0;
      }
      if (typeof(l) === "string") {
        return l.split('\n').filter(Boolean).length;
      }
      return l.length;
    },
    addStep: function() {
      this.editableObject['steps'].push({'step_type': 'driver',
                                         'arguments': {'conditions': '',
                                                       'customize': '',
                                                       'datatier': '',
                                                       'era': '',
                                                       'event_content': '',
                                                       'filein': '',
                                                       'fileout': '',
                                                       'process': '',
                                                       'step': '',
                                                       'scenario': ''},
                                         'input': {'dataset': '',
                                                   'lumisection': ''}});
    },
    deleteStep: function(index) {
      this.editableObject['steps'].splice(index, 1);
    },
  }
}
</script>

<style scoped>
h1 {
  margin: 8px;
}
td {
  padding-top: 2px;
  padding-bottom: 2px;
  padding-right: 4px;
}
.editPageCard {
  margin: auto;
  padding: 16px;
  max-width: 750px;
}
.checkbox-margin {
  margin: 0 !important;
  padding: 0 !important;
}
</style>
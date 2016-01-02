 function Attention(){
  this.ajax_method = 'GET';
}
Attention.prototype = {   //获取数据，重新画表
  call_sync_ajax_request:function(url, method, callback){
    $.ajax({
      url: url,
      type: method,
      dataType: 'json',
      async: false,
      success:callback
    });
  },
Draw_attention:function(data){
	//var UserID = uid;
    //var UserName = document.getElementById('nickname').innerHTML;
    //var select_graph = $('input[name="graph-type"]:checked').val();
    var texts = '';
	 var items = data;
	if(items==null){
		var say = document.getElementById('test1');
		say.innerHTML = '该用户暂无此数据';
	 }else{
		attention(items,UserID,UserName,texts);
        draw_topic(items['in_portrait_result']);
        draw_field(items['in_portrait_result']);
        draw_more_topic(items['in_portrait_result']);        
        draw_more_field(items['in_portrait_result']);
        draw_out_list(items['out_portrait_list']);
        draw_in_list(items['in_portrait_list']);
	 }	
  }
}
var Attention = new Attention();
url = '/attribute/attention/?uid='+uid+'&top_count='+select_num ;
Attention.call_sync_ajax_request(url, Attention.ajax_method, Attention.Draw_attention);
function attention(data,UserID,UserName,texts){
    out_data = data['out_portrait_list'];
    in_data = data['in_portrait_list'];
    var personal_url = 'http://'+ window.location.host + '/index/personal/?uid=';
    var nod = {};
    nodeContent = []
    nod['category'] = 0;
    nod['name'] = UserName;
    nod['value'] = 10;
    nodeContent.push(nod);
    for (i=0;i<out_data.length;i++){
            nod = {};
            //console.log(data[i][1][2]);
            nod['category'] = 2;
            nod['name'] = out_data[i][0];
            nod['label'] = out_data[i][1];
            nod['value'] = out_data[i][3];
            nodeContent.push(nod);
    }
    for (i=0;i<in_data.length;i++){
            nod = {};
            //console.log(data[i][1][2]);
            nod['category'] = 1;
            nod['name'] = in_data[i][0]
            nod['label'] = in_data[i][1];
            nod['value'] = in_data[i][4];
            nodeContent.push(nod);
    }    
    var linkline =[];
    for (i=0;i<in_data.length;i++){
        line ={};
        line['source'] = in_data[i][0];
        line['target'] = UserName;
        line['weight'] = 1;
        linkline.push(line);
    }
    for (i=0;i<out_data.length;i++){
        line ={};
        line['source'] = out_data[i][0];
        line['target'] = UserName;
        line['weight'] = 1;
        linkline.push(line);
    }
	var myChart3 = echarts.init(document.getElementById('test1'));
	var option = {
            title : {
                text: texts,
                x:'left',
                y:'top'
            },
            legend: {
                x: 'right',
                data:['用户','未入库','已入库']
            },
            series : [
                {
                    type:'force',
                    name : "人物关系",
                    ribbonType: false,
                    categories : [
                        {
                            name: '用户'
                        },
                       {
                            name:'已入库'
                        },
						{
                            name:'未入库'
                        },
                    ],
                    itemStyle: {
                        normal: {
                            color:function(param){
                                if(param.series.nodes[param.dataIndex].value == '9'){
                                    return 'red';
                                }
                                else if(param.series.nodes[param.dataIndex].value == '8'){
                                    return 'blue';
                                }
                                else if(param.series.nodes[param.dataIndex].value == '7'){
                                    return 'yellow';
                                }
                            },
                            label: {
                                show: true,
                                textStyle: {
                                    color: '#333'
                                }
                            },
                            nodeStyle : {
                                brushType : 'both',
                                borderColor : 'rgba(255,215,0,0.4)',
                                borderWidth : 1
                            },
                            linkStyle: {
                                type: 'curve'
                            }
                        },
                        emphasis: {
                            label: {
                                show: false
                                // textStyle: null      // 默认使用全局文本样式，详见TEXTSTYLE
                            },
                            nodeStyle : {
                                //r: 30
                            },
                            linkStyle : {}
                        }
                    },
                    useWorker: false,
                    minRadius : 15,
                    maxRadius : 25,
                    gravity: 1.1,
                    scaling: 1.1,
                    roam: 'move',
                    nodes:nodeContent,
                    links : linkline
                }
            ]
    };  
	myChart3.setOption(option);	
    require([
            'echarts'
        ],
        function(ec){
            var ecConfig = require('echarts/config');
            function focus(param) {
                var data = param.data;
                var links = option.series[0].links;
                var nodes = option.series[0].nodes;
                if (
                    data.source != null
                    && data.target != null
                ) { //点击的是边
                    var sourceNode = nodes.filter(function (n) {return n.name == data.source})[0];
                    var targetNode = nodes.filter(function (n) {return n.name == data.target})[0];
                    } else {
                    var node_url;
                    var weibo_url ;
                    var ajax_url ;
                    if(data.category == 0){
                        ajax_url = '/attribute/identify_uid/?uid='+UserID;
                        weibo_url = 'http://weibo.com/u/'+ UserID;
                        node_url = personal_url + UserID;
                    }else{
                        ajax_url = '/attribute/identify_uid/?uid='+data.name; 
                        weibo_url = 'http://weibo.com/u/'+ data.name;
                        node_url = personal_url + data.name;
                    }                 
                    $.ajax({
                      url: ajax_url,
                      type: 'GET',
                      dataType: 'json',
                      async: false,
                      success:function(data){
                        if(data == 1){
                            window.open(node_url);
                        }
                        else{
                            window.open(weibo_url);
                        }
                      }
                    });
                    
                }
            }
                myChart3.on(ecConfig.EVENT.CLICK, focus)

                myChart3.on(ecConfig.EVENT.FORCE_LAYOUT_END, function () {
                });
            }
    )   
}


function draw_topic(data){
    $('#topic').empty();
    var datas = data['topic'];
    html = '';
    html += '<table class="table table-striped table-bordered bootstrap-datatable datatable responsive">';
    html += '<tr><th style="text-align:center">排名</th><th style="text-align:center">话题</th><th style="text-align:center">次数</th></tr>';
    var i = 1;
    for (var key in datas) {
       html += '<tr><th style="text-align:center">' + i + '</th><th style="text-align:center">' + key + '</th><th style="text-align:center">' + datas[key] +  '</th></tr>';
       i = i + 1;
       if(i >=6 ){
        break;
       }
  }
    html += '</table>'; 
    $('#topic').append(html);                  
}

function draw_more_topic(data){
    $('#topic0').empty();
    var datas = data['topic'];
    html = '';
    html += '<table class="table table-striped table-bordered bootstrap-datatable datatable responsive">';
    html += '<tr><th style="text-align:center">排名</th><th style="text-align:center">话题</th><th style="text-align:center">次数</th></tr>';
    var i = 1;
    for (var key in datas) {
       html += '<tr><th style="text-align:center">' + i + '</th><th style="text-align:center">' + key + '</th><th style="text-align:center">' + datas[key] +  '</th></tr>';
    i = i + 1;
  }
    html += '</table>'; 
    $('#topic0').append(html);                  
}

function draw_field(data){
    $('#field').empty();
    var datas = data['domain'];
    html = '';
    html += '<table class="table table-striped table-bordered bootstrap-datatable datatable responsive">';
    html += '<tr><th style="text-align:center">排名</th><th style="text-align:center">领域</th><th style="text-align:center">次数</th></tr>';
    var i = 1;
    for (var key in datas) {
       html += '<tr><th style="text-align:center">' + i + '</th><th style="text-align:center">' + key + '</th><th style="text-align:center">' + datas[key] +  '</th></tr>';
       i = i + 1;
       if(i >=6 ){
        break;
       }
  }
    html += '</table>'; 
    $('#field').append(html);                  
}

function draw_more_field(data){
    $('#field0').empty();
    var datas = data['domain'];
    html = '';
    html += '<table class="table table-striped table-bordered bootstrap-datatable datatable responsive">';
    html += '<tr><th style="text-align:center">排名</th><th style="text-align:center">领域</th><th style="text-align:center">次数</th></tr>';
    var i = 1;
    for (var key in datas) {
       html += '<tr><th style="text-align:center">' + i + '</th><th style="text-align:center">' + key + '</th><th style="text-align:center">' + datas[key] +  '</th></tr>';
    i = i + 1;
  }
    html += '</table>'; 
    $('#field0').append(html);                  
}


function draw_out_list(data){
    $('#out_list').empty();
    html = '';
    html += '<table class="table table-striped table-bordered bootstrap-datatable datatable responsive">';
    html += '<thead><tr><th>用户ID</th><th>昵称</th><th>转发数</th><th>粉丝数</th><th>' + '<input name="out_choose_all" id="out_choose_all" type="checkbox" value="" onclick="out_choose_all()" />' + '</th></tr></thead>';
    html += '<tbody>';
    for(var i = 0; i<data.length;i++){
      var item = data[i];
      //item = replace_space(item);
      //global_data[item[0]] = item; // make global data
      user_url = 'http://weibo.com/u/'+ item[0];
      html += '<tr id=' + item[0] +'>';
      html += '<td class="center" name="uids"><a href='+ user_url+ '  target="_blank">'+ item[0] +'</td>';
      html += '<td class="center" style="width:150px;">'+ item[1] +'</td>';
      html += '<td class="center" style="width:100px;">'+ item[2] +'</td>';
      html += '<td class="center" style="width:100px;">'+ item[3] +'</td>';
      html += '<td class="center"><input name="out_list_option" class="search_result_option" type="checkbox" value="' + item[0] + '" /></td>';
      html += '</tr>';
    }
    html += '</tbody>';
    html += '</table>';
    $('#out_list').append(html);
}


function draw_in_list(data){
    $('#in_list').empty();
    html = '';
    html += '<table class="table table-striped table-bordered bootstrap-datatable datatable responsive">';
    html += '<thead><tr><th  style="width:95px;">用户ID</th><th style="width:150px;">昵称</th><th>影响力</th><th>重要性</th><th>转发数</th><th>' + '<input name="in_choose_all" id="in_choose_all" type="checkbox" value="" onclick="in_choose_all()" />' + '</th></tr></thead>';
    html += '<tbody>';
    for(var i = 0; i<data.length;i++){
      var item = data[i];
      //item = replace_space(item);
      //global_data[item[0]] = item; // make global data
      user_url = 'http://weibo.com/u/'+ item[0];
      html += '<tr id=' + item[0] +'>';
      html += '<td class="center" name="uids"><a href='+ user_url+ '  target="_blank">'+ item[0] +'</td>';
      html += '<td class="center" style="width:150px;">'+ item[1] +'</td>';
      html += '<td class="center" >'+ item[2].toFixed(2) +'</td>';
      html += '<td class="center" >'+ item[3].toFixed(2) +'</td>';
      html += '<td class="center" >'+ item[4] +'</td>';
      html += '<td class="center"><input name="in_list_option" class="search_result_option" type="checkbox" value="' + item[0] + '" /></td>';
      html += '</tr>';
    }
    html += '</tbody>';
    html += '</table>';
    $('#in_list').append(html);
}

function out_choose_all(){
  $('input[name="out_list_option"]').prop('checked', $("#out_choose_all").prop('checked'));
}
function in_choose_all(){
  $('input[name="in_list_option"]').prop('checked', $("#in_choose_all").prop('checked'));
}

function out_list_button(){
  var cur_uids = []
  $('input[name="out_list_option"]:checked').each(function(){
      cur_uids.push($(this).attr('value'));
  });
  var compute_type = $('input[name="compute-type"]:checked').val();
  var recommend_date = getDate();
  if (compute_type==2){
    var a = confirm('确定要推荐入库吗？');
    if (a == true){
        var compute_url = '/recommentation/identify_in/?date='+recommend_date+'&uid='+cur_uids+'&status'+compute_type;
        console.log(compute_url);
        Attention.call_sync_ajax_request(url, Attention.ajax_method, confirm_ok);
    }
  }
  else{
      compute_time = '1';
      var sure = confirm('立即计算会消耗系统较多资源，您确定要立即计算吗？');
      if(sure==true){
          //console.log(compute_time);
          $('#recommend').empty();
          var waiting_html = '<div style="text-align:center;vertical-align:middle;height:40px">数据正在加载中，请稍后...</div>';
          $('#recommend').append(waiting_html);

        var recommend_confirm_url = '/recommentation/identify_in/?date=' + recommend_date + '&uid_list=' + uids_trans + '&status=' + compute_time;
          //console.log(recommend_confirm_url);
          draw_table_recommend.call_sync_ajax_request(recommend_confirm_url, draw_table_recommend.ajax_method, confirm_ok);    
          var url_recommend_new = '/recommentation/show_in/?date=' + $("#recommend_date_select").val();
          draw_table_recommend_new = new Search_weibo_recommend(url_recommend_new, '#recommend');
          draw_table_recommend_new.call_sync_ajax_request(url_recommend_new, draw_table_recommend_new.ajax_method, draw_table_recommend_new.Re_Draw_table);
        var url_history_new = '/recommentation/show_compute/?date=' + $("#history_date_select").val();
          draw_table_history_new = new Search_weibo_history(url_history_new, '#history');
          draw_table_history_new.call_sync_ajax_request(url_history_new, draw_table_history_new.ajax_method, draw_table_history_new.Re_Draw_table);
      }    
  }
}

function in_list_button(){
  var group_confirm_uids = [];
  $('input[name="in_list_option"]:checked').each(function(){
      group_confirm_uids.push($(this).attr('value'));
  })
  console.log(group_confirm_uids);
  var group_ajax_url = '/group/submit_task/';
  var group_url = '/index/group_result/';
  var group_name = $('input[name="so_group_name"]').val();
  var remark = $('input[name="so_states"]').val();
  console.log(group_name, remark);
  if (group_name.length == 0){
      alert('群体名称不能为空');
      return;
  }
  var reg = "^[a-zA-Z0-9_\u4e00-\u9fa5\uf900-\ufa2d]+$";
  if (!group_name.match(reg)){
    alert('群体名称只能包含英文、汉字、数字和下划线,请重新输入!');
    return;
  }
  if ((remark.length > 0) && (!remark.match(reg))){
    alert('备注只能包含英文、汉字、数字和下划线,请重新输入!');
    return;
  }
  if(group_confirm_uids.length <1){
    alert("请选择至少1个用户");
    return ;
  }
  var job = {"task_name":group_name, "uid_list":group_confirm_uids, "state":remark};
  $.ajax({
      type:'POST',
      url: group_ajax_url,
      contentType:"application/json",
      data: JSON.stringify(job),
      dataType: "json",
      success: callback
  });
  function callback(data){
      console.log(data);
      if (data == '1'){
          window.location.href = group_url;
      }
      else{
          alert('已存在相同名称的群体分析任务,请重试一次!');
      }
  }
}

function getDate() {
    var date = new Date();
    var seperator = "-";
    var year = date.getFullYear();
    var month = date.getMonth() + 1;
    var strDate = date.getDate();
    if (month >= 1 && month <= 9) {
        month = "0" + month;
    }
    if (strDate >= 0 && strDate <= 9) {
        strDate = "0" + strDate;
    }
    var currentdate = year + seperator + month + seperator + strDate
    return currentdate;
}

function confirm_ok(data){
  //console.log(data);
  if(data)
    alert('操作成功！');
}
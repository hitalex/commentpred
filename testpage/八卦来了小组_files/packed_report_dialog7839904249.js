function generate_report_dialog(a){if(typeof(dui)=="undefined"){$.getScript("/js/ui/dialog.js",function(){_generate_report_dialog(a)})}else{_generate_report_dialog(a)}}function _generate_report_dialog(e){var d='<span class="up">举报已提交</span>';var i="http://help.douban.com/help/ask";var a="/j/misc/report_form";var f="/misc/audit_report";var b='<span>为了便于工作人员进行受理，请您通过豆瓣帮助中心<br ><a target="_blank" href="'+i+'">'+i+"</a>详细描述举报内容</span>";var j="<h3>提交详细信息</h3>";var h=e.report_url?e.report_url:"";var c=e.reason?e.reason:0;var g=dui.Dialog({title:(e.title?e.title:"选择举报原因"),url:(e.url?e.url:a),width:(e.width?e.width:442),cls:(e.cls?e.cls:"report-dialog")});if(!g.is_report_dlg_singleton){g.body.delegate(".btn-report","click",function(){c=$("#report_value input[type=radio]:checked").val();if(c=="other"){g.node.find(".hd").html(j);g.node.find(".bd").html(b);g.update();g.body.delegate(".bd a","click",function(){g.close()})}else{$.post_withck(f,{url:h,reason:c},function(){g.node.find(".hd").hide();g.node.find(".bd").html(d);g.update();setTimeout(function(){g.close()},1000)})}});g.is_report_dlg_singleton=true}g.open();g.node.find(".hd").show();g.update()};
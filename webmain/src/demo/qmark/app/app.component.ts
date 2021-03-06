import { Component } from '@angular/core';

@Component({
  selector: 'qmark-demo',
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.css']
})
export class AppComponent {
  title = '应用ABC';
  mdContent = questions;
}

let questions = `\
##1 单选题
为验证程序模块A是否正确实现了规定的功能，需要进行 __(1)__；
为验证模块A能否与其他模块按照规定方式正确工作，需要进行__(2)__。

  ~~~python
  def f():
    a = 1
  ~~~

###1 单选题 一行四项
  (A): 单元测试
  (B): 集成测试
  (C, 整行): 确认测试
  (D): 系统测试

  %%% 答案  (A)

###2 单选题 一行四项
  (A): 单元测试
  (B): 集成测试
  (C): 确认测试
  (D): 系统测试

  %%% 答案：(B)

##1 单选题
为验证程序模块A是否正确实现了规定的功能，需要进行 __(1)__；
为验证模块A能否与其他模块按照规定方式正确工作，需要进行__(2)__。

(A): 单元测试
(B): 集成测试
(C): 确认测试
(D): 系统测试

%%% 答案 1. (A) ; 2. (B)
`;
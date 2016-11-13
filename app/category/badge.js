import "./badge.css!"

angular.module('mainapp').controller('badgeCardCtrl', badgeCardCtrl);
badgeCardCtrl.$inject = ['$scope', '$element', '$attrs'];
function badgeCardCtrl($scope, $element, $attrs) {
  let $ctrl = this;

  $ctrl.saveForLater = function() {
    let question = $scope.question;
    if (!question.saveForLater) {
      question.saveForLater = {
        taggedTime: new Date()
      };
    } else {
      question.saveForLater = null;
    }
  };

  $ctrl.addToKnowledge = function(category) {
    category = angular.copy(category);
    category.taggedTime = new Date();
    $scope.question.categories[category.label] = category;
  };

  $ctrl.addTag = function(tag) {
    tag = angular.copy(tag);
    tag.taggedTime = new Date();
    $scope.question.tags[tag.label] = tag;
  };

  $ctrl.removeCategory= function(label) {
    delete $scope.question.categories[label];
  }


  $ctrl.removeTag= function(label) {
    delete $scope.question.tags[label];
  }
}


angular.module('mainapp').directive('questionBadgeBar', questionBadgeBar);
questionBadgeBar.$inject = ['$compile', '$timeout'];
function questionBadgeBar($compile, $timeout) {
  return {
    restrict: 'EA',
    replace: true,
    scope: {
      question: '=',
      repository: '='
    },
    templateUrl: 'app/category/badge.html',
    controller: 'badgeCardCtrl',
    controllerAs: '$ctrl',
    link: function($scope, $element, $attrs, ctrl) {
      // if ($attrs.purpose) {
      //   $scope.$parent.$watch($attrs.purpose, purpose => {
      //     // $scope.purpose = makeCatgeoryDictTuple(categories);
      //   }, true);
      // }

      // $scope.$watch('question.questionStyle', questionStyle => {
      // });

      // $scope.allCategories = {};
      // $scope.allTags = {};
      $scope.hovers = {};

      $scope.$parent.$watch('question.categories', categories => {
        let repo = $scope.repository;
        $scope.categoryList = convertToList(categories, repo.categories);
        console.log(344555, $scope.categories);
      }, true);

      $scope.$parent.$watch('question.tags', tags => {
        let repo = $scope.repository;
        $scope.tagList = convertToList(tags, repo.tags);
      }, true);

    }
  }

  /** [[{cat_item_1...}, {cat_item_2a, cat_item_2b, ...} ], ...] */
  function convertToList(categories, allCategories) {

    let data = {};
    for (label of Object.keys(categories)) {
      let labelParts = label.split('/', 2)
      if (labelParts.length == 2) {
          let level1_label = labelParts[0];
          let level1_item = data[level1_label];
          if (!level1_item) {
            level1_item = categories[level1_label];
            if (!level1_item) {
              level1_item = allCategories[level1_label];
              if (!level1_item) {
                level1_item = { label: level1_label };
              }
            }

            level1_item = [level1_item, []];
            data[level1_label] = level1_item;
          }

          item = categories[label];
          item.name = labelParts[1];
          level1_item[1].push(item);

      } else if (labelParts.length == 1) {
        data[label] = [categories[label], []]
      } else {
        console.error('!!!');
      }
    }

    return Object.keys(data).sort().map(label => {
      let item = data[label];

      let level2Items;
      level2Items = item[1].sort((a, b) => {
        if (a.label < b.label) {
          return -1;
        }
        if (a.label > b.label) {
          return 1;
        }
        return 0;
      });;

      return [item[0], level2Items]
    });

  }
}
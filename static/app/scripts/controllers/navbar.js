'use strict';

/**
 * @ngdoc function
 * @name weberApp.controller:NavbarCtrl
 * @description
 * # NavbarCtrl
 * Controller of the weberApp
 */
angular.module('weberApp')
.directive('navbardirective', function () {
    return {
        restrict: 'A', //This menas that it will be used as an attribute and NOT as an element. I don't like creating custom HTML elements
        replace: true,
        scope:true,
        templateUrl: "/static/app/views/navbar.html",
        controller: "navbarcontroller"
  }
})
    .controller('navbarcontroller',function($scope, $auth, CurrentUser, $alert,$rootScope,$timeout,InstanceSearch,
                                            $location, $http, Restangular,ChatActivity, $window,UserService,
                                            CurrentUser1,SearchActivity,FriendsNotific,friendsActivity,$socket) {
    $scope.selectedAddress = '';
      $scope.getAddress = function(viewValue) {
        var params = {address: viewValue, sensor: false};
        return $http.get('http://maps.googleapis.com/maps/api/geocode/json', {params: params})
        .then(function(res) {
          return res.data.results;
        });
      };
    $scope.instancesearch = new InstanceSearch();
    $scope.testingsearch = function(){
       $scope.instancesearch.getInstancePeoples(this.InstanceSearchQuery)
    }

    $scope.UserService = UserService

    $scope.dropdown = [{
        "text": "Settings",
        "href": "#/settings"
    },{
        "text": "Logout",
        "click": "logout()"
    }];

    $scope.logout = function() {
    //CurrentUser.reset();
        $rootScope.isloggin = false;
        $window.sessionStorage.clear();
        $auth.logout();
        $location.path("/search");
    };

    $scope.isAuthenticated = function() {
        return $auth.isAuthenticated();
    };

    $http.get('/api/me', {
        headers: {
            'Content-Type': 'application/json',
            'Authorization': $auth.getToken()
        }
    }).success(function(user_id) {

        Restangular.one('people',JSON.parse(user_id)).get({seed: Math.random()}).then(function(user) {

            $socket.emit('connecting', {id:user._id});
            $socket.on('joiningstatus', function(data) {
                console.log(data)
            });

        // popup notifications code
            $scope.menuOpened = false;
            $scope.notificationOpened = false;
            $scope.notificationMenu = function(event) {
                $scope.notificationOpened = !($scope.notificationOpened);
                event.stopPropagation();
            };

            $scope.menuMenu = function(event) {
                $scope.menuOpened = !($scope.menuOpened);
                event.stopPropagation();
            };
            //console.log($window)

            $window.onclick = function() {
                if ($scope.menuOpened) {
                  $scope.menuOpened = false;
                  //console.log("------------------------------------------------")

                // You should let angular know about the update that you have made, so that it can refresh the UI
                  $scope.$apply();
                }

                if ($scope.notificationOpened) {
                  $scope.notificationOpened = false;

                // You should let angular know about the update that you have made, so that it can refresh the UI
                  $scope.$apply();
                }

            };
        // end of popup notifications

        $scope.searchActivity = new SearchActivity($scope.currentUser)
        $scope.loadSearchHistory = function(){
            $scope.searchActivity.getMysearches();
        }

        var requested_peoples = [];
        var accepted_peoples = [];

        function get_friend_notifications(currentUser){

            var notific = new FriendsNotific(currentUser);
            notific.then(function(data){

                    accepted_peoples = [];
                    var currentuser = data
                    var k = null;
                    for (k in currentuser.notifications){
                        if(currentuser.notifications[k].seen == false){
                            requested_peoples.push(currentuser.notifications[k].friend_id)
                        }
                    }

                    k= null;
                    for (k in currentuser.accept_notifications){
                        if(currentuser.accept_notifications[k].seen == false){
                            accepted_peoples.push(currentuser.accept_notifications[k].accepted_id)
                        }
                    }


                    if(requested_peoples.length+accepted_peoples.length > 0){
                        if(!(currentUser.all_seen)){
                            $scope.newnotific = requested_peoples.length+accepted_peoples.length
                        }else{
                            $scope.newnotific = null;
                        }
                    }else{
                        $scope.newnotific = null;
                    }
            });
        }

        function getMatchButtonNotific(currentuser){

            $scope.unseenMnotific = []
            $scope.matchnotifications = currentuser.matchnotifications
            for(var temp in currentuser.matchnotifications){
                if(currentuser.matchnotifications[temp].seen == false &&
                   currentuser.matchnotifications[temp].interestedperson != user._id){
                    $scope.unseenMnotific.push(currentuser.matchnotifications[temp])
                }
            }
        }


        $socket.on('FMnotific', function(data){
            if(data.data.FMnotific){
                $http.get('/api/me', {
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': $auth.getToken()
                    }
                }).success(function(user_id) {
                    Restangular.one('people',JSON.parse(user_id)).get({seed: Math.random()})
                    .then(function(user) {
                            get_friend_notifications(user);
                            getMatchButtonNotific(user);
                    });
                });
            }
        });


        get_friend_notifications(user);
        getMatchButtonNotific(user);

        $scope.getNewNotifcations = function(){
            //$scope.MatchButtonNotific = null;
            if($scope.newnotific || $scope.unseenMnotific.length ){

                $scope.tempUnseen = $scope.unseenMnotific;
                $scope.unseenMnotific = [];

                $scope.newnotific = null;
                $scope.MatchButtonNotific = null;
                $http.get('/api/me', {
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': $auth.getToken()
                    }
                }).success(function(user_id) {
                    Restangular.one('people',JSON.parse(user_id)).get({seed: Math.random()}).then(function(user) {


                            var anotific = [];
                            var reqnotific = [];
                            var k = null;

                            for(k in user.accept_notifications){
                                user.accept_notifications[k].seen = true
                                anotific.push(user.accept_notifications[k].accepted_id)
                            }

                            k = null;

                            for(k in user.notifications){
                                user.notifications[k].seen = true
                                reqnotific.push(user.notifications[k].friend_id)
                            }

                            if($scope.tempUnseen.length){
                                for(var k in user.matchnotifications){
                                    if(user.matchnotifications[k].seen == false){
                                        user.matchnotifications[k].seen = true;
                                    }
                                }
                            }

                            user.patch({
                                'all_seen':true,
                                'accept_notifications':user.accept_notifications,
                                'notifications': user.notifications,
                                'matchnotifications': user.matchnotifications
                            }).then(function(data){
                                console.log(data)
                            });


                            var params = '{"_id": {"$in":["'+(reqnotific).join('", "') + '"'+']}}'
                            Restangular.all('people').getList({
                                where : params,
                                seed: Math.random()
                            }).then(function(response){
                                $scope.rpeoples = response;
                            });

                            var params = '{"_id": {"$in":["'+(anotific).join('", "') + '"'+']}}'
                            Restangular.all('people').getList({
                                where : params,
                                seed: Math.random()
                            }).then(function(resposne){
                                $scope.apeoples = resposne;
                            });
                        });
                    });
               }
         }

         $scope.openchatroom = function(id){
            if(!(sessionStorage.getItem(id))){
                var json = {};
                Restangular.one('people', id).get({seed: Math.random()})
                .then(function(data){
                    json = {
                        name:data.name.first,
                        id: data._id,
                        image:data.picture.medium,
                        minimize:false,
                        maximize:true,
                        right:0,
                        height:'364px'
                    }

                    sessionStorage.setItem(id, JSON.stringify(json));
                    $socket.emit('connect', {data:id});
                    $rootScope.chatactivity.loadMessages(user._id, id, json);
                });
            }
        }
    });
});
})
.directive('getuserdata', function () {
    return {
        controller:function($scope, CurrentUser1,$http,Restangular,$auth){
            $http.get('/api/me', {
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': $auth.getToken()
                }
            }).success(function(user_id) {
                Restangular.one('people',JSON.parse(user_id)).get({seed: Math.random()}).then(function(user) {
                    $scope.currentUser = user;
                });
            });
        }
    }
});

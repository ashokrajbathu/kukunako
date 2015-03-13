'use strict';

/**
 * @ngdoc function
 * @name weberApp.controller:NavbarCtrl
 * @description
 * # NavbarCtrl
 * Controller of the weberApp
 */
angular.module('weberApp')
.directive('navbar', function () {
    return {
        restrict: 'A', //This menas that it will be used as an attribute and NOT as an element. I don't like creating custom HTML elements
        replace: true,
        scope:true,
        templateUrl: "/static/app/views/navbar.html",
        controller: "navbarcontroller"
  }
})
    .controller('navbarcontroller',function($scope, $auth, CurrentUser, $alert,$rootScope,$timeout,
                                            $location,$http,Restangular,ChatActivity, $window,
                                            CurrentUser1,SearchActivity,FriendsNotific,friendsActivity,$socket) {
    //$scope.data = CurrentUser1;
    /*$timeout(function(){
        console.log($scope.data)
    }, 10000);*/
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

             // Listening to an event
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
            console.log($window)

            $window.onclick = function() {
                if ($scope.menuOpened) {
                  $scope.menuOpened = false;
                  console.log("------------------------------------------------")

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


        get_friend_notifications(user);

          $socket.on('friendnotifications', function(data){
            console.log(data)
            /*if(parseInt(data.searchNotific)){
                $scope.searchActivity = new SearchActivity(user);
            }*/

            if(data.data.friendsnotifc){

                $http.get('/api/me', {
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': $auth.getToken()
                    }
                }).success(function(user_id) {
                    Restangular.one('people',JSON.parse(user_id)).get({seed: Math.random()})
                    .then(function(user) {
                            get_friend_notifications(user);
                    });

                });
            }

        });

        $scope.getNewNotifcations = function(){

            $scope.newnotific = null;
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

                        user.patch(
                        {	'all_seen':true,
                            'accept_notifications':user.accept_notifications,
                            'notifications': user.notifications
                        }
                        ).then(function(data){
                            console.log('updated accept notifications')
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

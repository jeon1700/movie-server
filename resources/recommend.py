from flask import request
from flask_jwt_extended import get_jwt_identity, jwt_required
from flask_restful import Resource
import pandas as pd
from mysql_connection import get_connection
from mysql.connector import Error


class MovieRecommendResource(Resource) :

    @jwt_required()
    def get(self) :

        user_id = get_jwt_identity()

        # 1. 영화별로 상관계수를 뽑아야 한다.
        # 1-1. DB에서 movie테이블 과 review테이블 의 데이터를 가져와서, 데이터프레임을 만든다.
        try : 
            connection = get_connection()
            query = '''select m.id as movieid, m.title, r.userid, r.rating
                        from movie m
                        left join review r 
                        on m.id = r.movieid ;'''
            
            cursor = connection.cursor(dictionary= True)
            cursor.execute(query, )

            result_list = cursor.fetchall()
            
        # 1-2. 데이터프레임의 모양을, 상관계수 계산할수 있도록, pivot_table 해야 한다. 
            df = pd.DataFrame(result_list)
            
            print(df)
            
            df = df.pivot_table(index='userid', columns= 'title', values= 'rating', aggfunc= 'mean')
        

        
        # 1-3. corr() 함수를 이용해서 상관계수를 뽑는다.
            corr_movie = df.corr(min_periods=40) #min_periods= ~~ 적어도 ~~개 는 있어야한다.



        # 2. 이 유저의 별점 정보를 DB에서 가져온다.(가중치 계산)  
            query = '''select m.title, r.rating
                        from review r
                        join movie m
                        on r.movieid = m.id 
                        where r.userid = %s;'''
            
            record = (user_id , )
            
            cursor = connection.cursor(dictionary= True)
            cursor.execute(query,record)

            result_list = cursor.fetchall()
            
            print()
            print(result_list)
            print()

            cursor.close()
            connection.close()

        except Error as e:
            print(e)
            cursor.close()
            connection.close()
            return {'error' : str(e)}, 500
        


        # 3. 가중치로 계산하여 응답한다. 
        my_rating = pd.DataFrame(result_list)

        movie_list = pd.DataFrame()
        for i in range(my_rating.shape[0]):
            title = my_rating['title'][i]
            recom_movie = corr_movie[title].dropna().sort_values(ascending= False).to_frame()
            recom_movie.columns = ['corr']
            recom_movie['weight'] = recom_movie['corr'] * my_rating['rating'][i]
            
            movie_list = pd.concat([movie_list,recom_movie])



        # 3-1. 이미 본 영화 및 중복 영화 제거한다.
        for title in my_rating['title'] :
            if title in movie_list.index :
                movie_list.drop(title, axis = 0, inplace=True)

        movie_list = movie_list.groupby('title')['weight'].max().sort_values(ascending=False).head(10)


        print()
        print(movie_list)
        print()

        # 위의 코드는 판다스의 시리즈 이므로 이를 JSON으로 바꿔서 보내는 방법
        movie_list = movie_list.to_frame().reset_index().to_dict('records')


        return {'result' : 'success',
                'items' : movie_list ,
                'count' : len(movie_list)}
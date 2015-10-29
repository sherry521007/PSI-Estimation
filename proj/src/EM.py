import scipy as scp
import scipy.optimize as opt
import numpy as np
import json

class EMAlgorithm:
    def __init__(self, NG, NE, NW, K):
        self.NG = NG
        self.NE = NE
        self.K = K
        self.NW = NW
        self.NA = []
        for g in range(self.NG):
            self.NA.append(int(np.round(0.5 * (self.NE[g] * self.NE[g] + 5 * self.NE[g] - 4))))
        self.NX = []
        for g in range(self.NG):
            self.NX.append(int(np.round(0.5 * (self.NE[g] * self.NE[g] + self.NE[g]))))
        
        self.L = []
        for g in range(self.NG):
            self.L.append(np.random.rand(1, self.NX[g]))
        
        self.C = []
        for s in range(self.NW):
            self.C.append([])
            for g in range(self.NG):
                self.C[s].append(np.random.rand(1, self.NX[g]))
        
        self.Tau = []
        for s in range(self.NW):
            self.Tau.append([])
            for g in range(self.NG):
                self.Tau[s].append(np.random.rand(1, self.NX[g]))
        
        self.W = np.random.rand(1, self.NW)
        self.Z = np.random.rand(1, self.NG)
        self.X = []
        for g in range(self.NG):
            self.X.append(np.random.rand(1, self.NX[g]))
            
        self.Mu = np.random.rand(self.NW, self.NG)
        self.A = []
        for g in range(self.NG):
            self.A.append(np.random.rand(self.NA[g], self.NX[g]))

        self.initialByKmerTable()

    def initialByKmerTable(self):        
        for s in range(self.NW):
            for g in range(self.NG):
                self.Tau[s][g] = self.C[s][g]/self.L[g]
                
        json.load()
        
        return
    
    def initialVariables(self):
        return        
    
    def eStep(self):
        for s in range(self.NW):
            tot = 0.0
            for g in range(self.NG):
                self.Mu[s, g] = self.Z[0, g] * np.dot(self.C[s][g]/self.L[g], self.X[g].T)[0, 0]
                tot += self.Mu[s, g]
            for g in range(self.NG):
                self.Mu[s, g] /= tot 
        return
    
    def mStep(self):
        tot = 0.0
        for g in range(self.NG):
            self.Z[0, g] = np.dot(self.W, self.Mu[:,g])
            tot += self.Z[0, g]
        for g in range(self.NG):
            self.Z[0, g] /= tot            
        for g in range(self.NG):
            self.optimizeQ(g)        
        return
    
    def optimizeQ(self, g):
        #=======================================================================
        # print(np.shape(self.A[g]))
        # I = (np.dot(self.A[g], self.X[g].T) == 0.)
        # idxA1 = []
        # for r in range(self.NA[g]):
        #     if I[r, 0]:
        #         idxA1.append(r)
        # A1 = self.A[g][idxA1,:]
        # E = np.ones((1, self.NE[g]))
        # print(A1)
        # print(E)
        # input()
        #=======================================================================
        X0 = (g, self.X[g].T)
        cons = ({'type': 'ineq', 'fun': lambda X: np.dot(self.A[X[0]], X[1])}, 
                {'type': 'eq', 'fun': lambda X: np.sum(X[1]) - 1})
        #res = opt.minimize(self.objectFunction, x0 = X0, constraints = cons)
        #self.X[g] = res.x[1]
        return
    
    def objectFunction(self, X):
        res = 0.0
        for s in range(self.NW):
            res += self.W[s] * self.Mu[s][X[0]] * np.log(self.Tau[s][X[0]], X[1])
        return res
    
    def work(self, time):
        self.initialByKmerTable()
        self.initialVariables()
        while time > 0:
            print(self.Z)
            self.eStep()
            self.mStep()
            time -= 1
        self.computePSI()
        return
    
    def computePSI(self):
        #=======================================================================
        # #Unit test for computing PSI
        # self.X = [np.matrix([[10,7,3,10,7,3,0,0,7,3]])]
        # self.L = [np.matrix([[1 ,1 ,1,1 ,1 ,1,1,1,1,1]])]
        # self.NG = 1
        # self.NX = [10]
        # self.NE = [4]
        #=======================================================================
        self.Psi = []
        for g in range(self.NG):
            tempPsi = self.X[g] / self.L[g]  
            sumEx = 0.0
            sumJu = 0.0
            for e in range(self.NX[g]):
                if e < self.NE[g]:
                    sumEx += tempPsi[0, e]
                else:
                    sumJu += tempPsi[0, e]
                e += 1
            tempPsi = tempPsi / (sumEx - sumJu)
            self.Psi.append(tempPsi[0,:self.NE[g]])         
        return
    
if __name__ == "__main__":
    test = EMAlgorithm(3, [2, 3, 5], 4, 25)
    test.work(100) 
    print(test.Psi)